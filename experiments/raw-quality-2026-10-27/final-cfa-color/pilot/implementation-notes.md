# Fixed final completion: implementation receipt

2026-10-27. **SOURCE PREPARATION ONLY.** No producer import, Torch/CUDA launch,
NVRTC compilation, numerical test, RAW read or render by the author. Current
native-spectral full299 sources remain unchanged. The root-owned stages and
bounds are in [brief.md](brief.md); the scientific contract is
[../design.md](../design.md), with the independent
[challenge](../challenge.md) and [API](api.md).

## Producing path and exact quantities

`spectral-completion.py` contains one completion. `complete` first applies the
held native preparation to the caller's immutable signed, black-subtracted
final CFA: max0, per-color green-normalized WB multiply, exposure-one multiply,
then division by the f32 level range. The explicit CUDA `__fmul_rn` and
`__fdiv_rn` prevent a reciprocal-multiply or fused arithmetic substitution at
this stage. The original `native-cfa-develop.rs` uses the same expression.
There is no second black subtraction and no new merged-noise estimate.

`complete_normalized` accepts finite signed normalized CFA and exercises exactly
the same completion code without preparing it again. This is the independent
small DFT commissioning seam; actual photographic input uses `complete`.
The native writer must receive returned normalized camera RGB directly, without
WB/range division, completion or clamp. It still applies the held camera matrix,
highlight handling, tone and ICC. Original signed CFA, actual normalized CFA,
and actual completed camera RGB are distinct saved quantities.

Per color, the operator fills the complete parity-preserving mirror-periodic
rectangle, zeros only missing color sites, performs orthonormal real FFT,
multiplies by the declared fixed real mask, inverse-transforms and crops. R/B
use square support; green combines both phases with diamond support. Integer
comparisons handle all axis/diamond boundaries for unequal even FFT dimensions.
No padding to a faster FFT shape, window, tile, cell-aperture inverse or filter
transition has been substituted. Constants and sampled-site identities are
algebraic claims to commission, not executed results.

Known-site error is collected before the known-site overwrite. Small inputs
also retain the entire pre-overwrite camera field for independent missing-site
comparison. The final output explicitly restores known normalized samples and
checks their bits. That cannot validate inferred sites; the wrong square-green,
swapped-R/B and doubled-gain diagnostics traverse the same producing path.
These are control foils, not alternative candidate recipes.

## Runtime and resource boundary

Module import uses only standard-library definitions. Construction privately
loads the exact frozen `dual-tree-cfa-gpu/ordered-fir.py` runtime (SHA256
`16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce`) and appends
three small independently written kernels for preparation, extension and mask
construction. It leaves the original helper and its CUDA text unchanged on
disk. Its strict whole-module no-floating-FMA PTX guard and options remain:
`--std=c++11`, the exact device architecture, `--fmad=false`, `--ftz=false`,
`--prec-div=true`, `--prec-sqrt=true`. There are no noise-transcendental functions
requiring the other pilot's relaxed scoped guard.

The driver launches use the current Torch context/stream, int64 flattened indices,
and Torch-owned storage with `record_stream`. The inherited unused ordered-FIR
entry points do not process this image. Metadata retains actual DLL/compiler,
driver, combined CUDA and PTX hashes, compiler log/options and completion-kernel
counters; strict completion metadata rechecks source and DLL bindings.

Signal is f32, spectrum complex64; TF32 and autocast are disabled. Colors are
processed sequentially. Full 6896x4596 becomes exactly 9190x13790 for each FFT.
The process receives an at-most8GiB Torch allocator cap; allocation/reservation
and their high-water values are reported. Driver and cuFFT plan storage outside
that allocator still need root's device/process accounting. No speed or full-size
workspace claim has been measured. Resource refusal must not select a different
boundary, precision, grid or recipe.

Per-color and total completion timing uses `time.perf_counter()` with explicit
CUDA synchronization. It includes per-color fill/FFT/mask/inverse/diagnostics/
restoration, but excludes constructor/NVRTC, normalization, caller I/O and native
writer. Root's whole-field cost must include those exclusions and all three
colors. The full spectrum/mask/extended field are released between colors.

**DERIVED liveness, not a measured peak:** at 6896x4596 the caller's signed CFA,
normalized CFA and final HWC RGB total 633,880,320 bytes. The extended real and
rFFT complex arrays are 506,920,400 and 506,993,920 bytes; the real mask is
253,496,960 bytes. The largest obvious simultaneous image set is about 1.65 GB,
plus FFT workspace and external plan/runtime storage. Green-site diagnostics
temporarily add about 0.25 GB after the spectrum is deleted. Full pre-restoration
RGB is retained only for <=16,384-pixel controls, not complete photographs.
Deleting a tensor releases liveness, not necessarily allocator reservations;
the reported reservation/high-water and root's full-shape cost remain necessary.

## Preserved limits and handoff

This fixed per-color bandwidth prior can preserve in-band independent chroma
and lose neutral detail above R/B Nyquist. The exact same-CFA/two-truth ambiguity
remains an adverse, not a promise to distinguish impossible inputs. Hard-mask
global ringing, affine reflection mismatch, and noisy missing-color samples
are explicit risks. Pre-MHC shared-bin/noise/alias failures are unchanged.
Neither linearity, restored known sites nor fewer cross-color terms proves a
better photograph.

Root's driver binds the producing source/runtime, held development, source CFA,
new normalized-camera writer and all control/report sources before and after
the run. It saves full normalized CFA/camera and native masters, then the fixed
whole-image/all-ten-witness views. The producer does no file writing, RAW decode,
source fusion or renderer invocation. Tensor version checks are supplementary:
inference-mode tensors have no counter, so their corresponding evidence is null,
not a claim that a file/input hash was checked.

The saved-field driver prospectively enforces the independent controls' per-color
known-site pre-restoration maximum/RMS bounds before native rendering: respectively
3e-6*max(1,reference maxabs) and 6e-7*max(1,reference RMS), using that color's
actual known normalized sites. It retains finite camera/CFA arrays and a failed
null receipt on refusal. This is a mechanical FFT/sampling check, not a threshold
on missing-color quality or a guarantee against the declared alias ambiguity.

Only source syntax/content verification is appropriate before root execution.
No product setting changes and no photographic admission are contained here.
