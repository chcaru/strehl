# Ordered forward FIR source revision

Source-only revision, 2026-10-27. No CUDA compilation, library import, numerical
test, RAW read or Rust build was performed by the author. The root schedules
the complete unchanged screen. This is an arithmetic-correspondence test, not
a photographic improvement claim or a relaxation of the failed first screen.

`gpu-server-convolution.py.txt` preserves the first server exactly, SHA256
`b17820bd8924d1ace1a76ae17dbc10465ccebe2782c0ffbae586d02d90c07fca`.
The new server is
`b40bead68adb6359ddf103b5cbba53bac97b9c4a9c4fc364b82dc61147dd1a4f`;
its pinned embedded-kernel helper `ordered-fir.py` is
`16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce`.

Only `Worker.__init__`, `Worker.forward` and `Worker.runtime` changed in the
server, plus the helper hash constant and standard-library `types` import.
An AST comparison verified every other function unchanged. Inverse FIR,
periodic adjoint folding, packing, filter constants, probes, smoothing, gates,
weights and finish/hull remain the first server's implementation. The protocol
and Rust consumer are unchanged. `ordered-fir-server.diff` records the exact
server source change.

Each kernel output is accumulated in ascending original tap order, using
`__fmul_rn` followed by `__fadd_rn`. Existing reversed correlation-tap tensors
are indexed backward to recover the CPU order; their bits are unchanged.
Source coordinates are `(2*m - minimum - j) mod extent`. The signed remainder
is corrected once into the positive range, including coarse extents shorter
than the filter. Horizontal output channels are tree low/high; vertical output
channels are branch low/high, retaining `LL,LH,HL,HH` for each tree. Source
strides are explicit, including the initial zero tree stride.

All image/filter/output storage stays in Torch's capped allocator. The helper
loads the installed Windows NVRTC and driver DLLs by absolute path, queries
their actual versions and supported compute architectures, and requires the
device's exact architecture. Options are C++11, that architecture,
`--fmad=false`, `--ftz=false`, `--prec-div=true`, `--prec-sqrt=true`.
PTX must contain explicit rounded f32 multiply/add and no floating FMA. Failure
refuses the worker; there is no alternate backend. Compilation time, log,
options and PTX hash/length are retained in runtime evidence.

The helper uses the already-current Torch CUDA context and actual current
stream, with `record_stream` on all participating tensors. It never creates,
pushes or replaces a context. DLL and module handles remain live until worker
exit. Driver module/JIT memory is explicitly outside Torch allocator accounting;
device-free memory before/after loading is descriptive, not an isolated module
allocation estimate or a total-device high-water measurement.

Runtime receipts bind helper/CUDA-source/PTX/DLL hashes, actual versions,
context/stream handles, launch census and compile options. Helper and DLL bytes
are rechecked before successful terminal evidence. No Rust change or rebuild
is required if the root's runtime-rebind check proves the frozen Rust/Cargo
inputs unchanged. The inverse and device log/exp still have their previously
declared arithmetic-order differences.

Author verification was only Python `ast.parse`, source SHA256, helper-pin
equality and the function-AST comparison. API facts were checked against the
official [NVRTC documentation](https://docs.nvidia.com/cuda/nvrtc/index.html),
[CUDA driver launch API](https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__EXEC.html)
and [single-precision CUDA intrinsics](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__SINGLE.html).
No third-party wavelet or CUDA algorithm implementation was consulted.
