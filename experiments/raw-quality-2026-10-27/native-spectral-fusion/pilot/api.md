# Fixed spectral pilot API

Source-only contract, 2026-10-27. Module `spectral-operator.py` avoids shadowing
the standard-library `operator` module. Import it by absolute file location;
importing the module uses only the standard library. CUDA compilation occurs
only when the root-scheduled caller constructs `SpectralConsumer`.

```python
Noise(black: float, gain4: tuple, read_variance4: tuple)
# Physical phase order R,G1,G2,B. Variance in DN^2:
# read_variance4[p] + gain4[p] * max(original_code-black, 0).

patch_origins(width: int, height: int, origin_xy=(0, 0)) -> list[tuple[int,int]]
# Row-major, local x in range(-64,width,64), y in range(-64,height,64),
# plus the even native origin_xy. Odd delivered dimensions are allowed.

SpectralConsumer(torch, device_limit_bytes=10 << 30)
engine.source(raw_u16, source_id: int, noise: Noise) -> Source
# raw_u16 is a contiguous NumPy/CPU/CUDA u16 [H,W] original active CFA.
# Upload/retain at most the current original u16 frame, never source RGB.

engine.geometry(origins, pull_affine, source_hw,
                diagnostic_green_square=False,
                diagnostic_phase_shift_xy=(0,0)) -> Geometry
# <=16 absolute reference-native patch origins. pull_affine is f64 2x3,
# maps reference-native integer sensel centers to source-native centers.
# Same f64 geometry applies to signal and every noise draw.

engine.lattice_samples(source, geometry, draw=None) -> dict
# {'R':f32[P,128,128], 'G':f32[P,256,256], 'B':f32[P,128,128]} CUDA.
# draw=None is black-subtracted original codes; draw=0..15 is a signed
# original-coordinate-indexed Gaussian probe with supplied variance.

engine.interpolate_lattices(lattices, geometry,
                            omit_cell_ratio=False) -> f32[P,4,64,64]
engine.gather(source, geometry, draw=None,
              omit_cell_ratio=False) -> f32[P,4,64,64]
engine.analyse(gathered) -> (complex64[P,4,64,64], f32[P,4])
engine.prepare_source(source, geometry, omit_cell_ratio=False) -> Prepared
# Prepared.gathered, .coefficients, .means, .variance, .admission, .evidence.
# Same actual gather for signal and all16 probes. V=sum(pairdiff power)/16.

Accumulator(engine, patch_count: int)
acc.add(patch_indices, prepared) -> None
# Exactly one contribution per source/patch, arbitrary sequential patch batches.
acc.finish() -> dict
# coefficients/uniform_coefficients complex64[P,4,64,64], means f32[P,4],
# counts int64[P], evidence. No output bypass for one source.

engine.overlap_add(finished, origins, width, height,
                   origin_xy=(0,0)) -> dict
# candidate/uniform f32[H,W] signed black-subtracted CFA, coverage f32[H,W].
# Optional patch subset returns zero outside coverage and complete_coverage=false;
# actual complete photograph requires all coverage>0. No hidden zero filling claim.
engine.metadata(strict=True) -> JSON-serializable dict
```

Geometry exposes `.origins`, `.lattice_origins` (CPU P x3 x2 integers, R/G/B),
`.query_lattice` (CUDA f64[P,4,64,64,2], relative to the chosen source lattice
origin), `.pull_affine` and `.evidence`. Reference offsets are R(0,0),G1(1,0),
G2(0,1),B(1,1). Source lattice origins are nearest-ties-even integers to
`mapped_patch_center_in_lattice - (N-1)/2`, independently for R/G/B.

The Hann is `sin(pi*n/64)^2`, separable, shared in quad coordinates. Its square
root is used for analysis/synthesis. Negative-half-window enumeration gives
positive coverage at all delivered corners, including odd last rows/columns.
Forced uniform uses the same collected coefficients/means and actual synthesis.

Source probes use one fixed integer counter hash and f32 Box-Muller, keyed by
source_id, draw_id and the **reflected original** row-major sensel index. All
overlapping/reflected occurrences and both green evaluations reuse that value.
`lattice_samples(...,draw=k)` exposes this exact producing path for identity
checks; distinct source IDs represent distinct acquisition noise. No RNG state
depends on batching or patch traversal. Kernel source pins the exact hash.

Diagnostic options are only control foils. Default production never shifts the
physical phase, substitutes a square green lattice, or omits the cell ratio.
All means/window reductions and FFT signal arithmetic are f32/complex64; only
geometry is f64. No Torch/CUDA operation has been executed by the author.
