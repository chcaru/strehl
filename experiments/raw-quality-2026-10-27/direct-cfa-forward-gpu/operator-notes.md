# Original-CFA measurement CUDA implementation

2026-10-27. **SOURCE-PREPARED / UNVERIFIED at runtime.** This file describes
`measurement-gpu.py`, a matrix-free implementation of the frozen CPU
`../joint-cfa-local-fit/band-residual/sensor-operator.py` Measurement operator
(SHA256 `536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac`).
It does not implement fitting, focus admission, a noise model, an image prior,
or photographic improvement. The earlier reconstruction's failed flat and
finite-iteration refusal are unchanged.

## Public API

```python
measurement = MeasurementGpu(torch, field_hw=(H, W), device_limit_bytes=8 << 30)
y = measurement.forward(x, source_xywh, source_to_latent_2x3)
back = measurement.adjoint(y, source_xywh, source_to_latent_2x3)
measurement.adjoint(y_piece, piece_xywh, source_to_latent_2x3, out=back)
receipt = measurement.metadata(strict=True)
```

`x` and `back` are contiguous Torch CUDA0 f32 HWC camera-RGB fields. `y` is a
contiguous CUDA0 f32 source-rectangle HW field. `source_xywh=(ox,oy,w,h)` uses
four Python integers in absolute original active-sensor coordinates, with
RGGB at `(0,0)`. The finite f64 2x3 affine maps those physical coordinates to
the **global** latent coefficient grid. Partitioning a source changes only
the source rectangle; neither global field nor affine changes. `out=None`
allocates a zero adjoint field; supplied `out` is accumulated into and returned.
The residual and supplied output may not overlap storage. The API does not
decode or change original u16 storage.

Global axes are 8..8192; source axes are 1..8192; a source rectangle contains
at most 1,048,576 sensels. Original coordinates are nonnegative signed-32-bit
range. Each affine linear row has absolute sum at most two and its determinant
must be nonzero. These bounds make the union of nine Lanczos stencils at most
8x8 sites. The root's later full-size cost worker must stream rectangles within
these bounds; no full-size sparse matrix or physical-node array is constructed.

## Producing rows and transpose

For every original sensel, the CUDA thread generates nine unit-square GL3
nodes: axes `(-sqrt(3/5)/2,0,+sqrt(3/5)/2)`, y-major then x, weights from the
tensor product `(5/18,4/9,5/18)`. It applies the complete affine to each physical
node in f64. At each node, six taps per axis have offsets -2..3 from the floor.
The f32 Lanczos3 formula and exact-integer special case match the CPU model;
each axis is normalized before its tensor product and footprint weight.

The thread coalesces the 9x36 contributions into a bounded 8x8 local array,
then divides that row by its f32 mass, as the CPU coalesces and normalizes its
sparse row. The channel is selected from original parity using `(0,1,1,2)`
for physical R,G1,G2,B. Both greens address the same latent green channel but
retain their distinct source coordinates. Forward is the row dot field;
adjoint uses the identical row helper and f32 atomic addition into the global
field. No RGB source image is constructed and no remosaic/demosaic is involved.

All six taps of every node must fit, including nominal zero taps. Host affine
corner/node preflight raises `ValueError` for unsupported support before any
caller-owned adjoint output is modified. CUDA checks every row independently.
Nonfinite weights, consumed values and touched accumulator values fail closed.
A runtime refusal after a launch invalidates a supplied adjoint accumulator;
the caller must discard it. Untouched latent sites are not rescanned on every
rectangle and remain the caller's responsibility.

## Arithmetic, runtime and evidence

The installed NVRTC/driver loader was adapted from our frozen
`../dual-tree-cfa-gpu/ordered-fir.py` (SHA256
`16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce`),
which was not edited or imported. No external implementation was consulted.
The supplied Torch instance owns a four-byte context-initialization allocation,
the global field, current rectangle and status. Driver launches use its current
CUDA0 context/stream; tensor `record_stream` calls preserve asynchronous
ownership. There is no new/pushed driver context. Compilation occurs only in
the root-scheduled constructor, never at module import.

Compiler options are C++11, exact detected device compute architecture,
`--fmad=false --ftz=false --prec-div=true --prec-sqrt=true`. Row products and
additions use explicit rounded f32 intrinsics; geometry uses explicit f64
products/additions. The f32 `sinf` implementation can differ from NumPy's
f32 sine, and libdevice may contain its own explicit FMAs. The receipt records
those PTX instructions without falsely claiming that all library internals
are FMA-free. Coalescing/reduction order differs from CPU sparse construction;
adjoint atomic addition is nondeterministic. Numerical equivalence under the
independently fixed bars is required; bit identity is not claimed.

Every call synchronizes its small status scalar and records elapsed wall time,
launch count and sensel count. The receipt rechecks helper, frozen CPU source
and CUDA DLL hashes, and records embedded CUDA/PTX hashes, compiler/log/version,
stream/context identities, Torch allocated/reserved peaks and module-load free
memory snapshots. The 8GiB declared Torch cap is checked before/after launches;
the root process also applies its allocator/process caps. Driver JIT code and
thread-local spills lie outside Torch accounting and are disclosed explicitly.
The control worker binds this source independently before/after execution.

The sole diagnostic override is `diagnostic_channel_map=(2,1,1,0)` or another
valid four-entry map, recorded as such. It reaches the same producing kernel
for the independently fixed wrong-channel foil. Wrong-coordinate controls pass
a perturbed affine through the ordinary API. No quality parameter, fallback,
support extension, solver or photographic admission is introduced here.

Author checks so far: standard-library `ast.parse` of this source and read-only
API comparison against independent controls; no Torch/NumPy import, CUDA
compilation, numerical execution, RAW read or build was performed by the author.
Root owns mechanical controls and any later full-source cost decision.
