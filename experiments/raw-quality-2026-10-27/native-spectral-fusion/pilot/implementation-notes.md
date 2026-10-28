# Fixed spectral pilot: source notes

2026-10-27. SOURCE PREPARATION ONLY. No Torch import, CUDA compilation, numerical
calculation, RAW read, build or render was performed by the author. The root
orchestrator alone schedules the following programs.

`spectral-operator.py` and [api.md](api.md) implement the fixed proposal. The
filename deliberately avoids the standard-library `operator` shadowing failure
encountered in the earlier band-residual pilot. The existing ordered-FIR file
is hash-bound at16688f2b and loaded into a private module. Its CUDA source is
retained and the new small extraction/Lagrange kernels are appended. All
buffers are Torch-owned and launched on the current Torch stream/context. This
does not modify any predecessor source. Metadata includes compiler options,
library/PTX hashes, source hashes, device high water and original-probe counts.

## Fixed geometry, Fourier and boundary conventions

The global native output origin is even. Patches are enumerated row-major with
local x in `range(-64,width,64)` and y in `range(-64,height,64)`. The real output
therefore has109 columns x73 rows =7957 patches. This corrects the design's
approximate108x72 storage estimate. The periodic64-point quad Hann is
`sin(pi*n/64)^2`; negative-half-window patches make coverage positive on all
four outer corners, including odd delivered extents. The producing OLA returns
its actual coverage; a partial cost batch never claims a complete image.

Each128-native patch center is origin+(63.5,63.5). Its held source pull gives
the source lattice center. R uses(x/2,y/2), B((x-1)/2,(y-1)/2), and green
((x+y-1)/2,(x-y-1)/2). Subtract(N-1)/2 and use nearest-ties-even rounding for
the integer lattice origin. Array columns are the first coordinate and rows
the second. G1/G2 retain their distinct output physical positions and share
the same green interpolant. Query coordinates remain f64 through floor and
fraction extraction; Lagrange arithmetic is f32. Flat-top support is checked
before FFT evaluation; failure does not enlarge, relocate or interpolate a
different source patch.

Native reflected coordinates use reflection about integer0 and dimension-1,
with period2*(dimension-1). Thus coordinate parity and CFA color are preserved.
The probe key is evaluated **after** reflection. Source IDs, absolute original
sensel indices and draw0..15 define the deterministic mix32/Box-Muller field.
Overlapping tiles, repeated reflection occurrences and both green evaluations
reuse a draw. These are16 original-sensor noise fields per source, evaluated
lazily, not16 new statistically independent fields per patch. Independent
controls must check temporal noise against the supplied model; spatial spread
of a scene is not that check.

All FFTs use `norm="ortho"`. Splitting even Nyquist frequencies precedes the
unit-cell ratio; each split edge gets1/2 and a split corner1/4. The4x-padded
unitary inverse is multiplied by4. Real conjugacy is reported via the maximum
discarded imaginary component. Mean-subtracted source taper, cell ratio,
interpolation, Hann analysis and coefficient covariance are the same for
signal and probes. Unit coefficient variance is1DN^2 under this normalization,
not an arbitrary threshold in unnormalized FFT units. No source MHC occurs.

The shared vector gate is a marginal-variance normalized power sum, not full
covariance whitening. It makes no chi-square or independent-bin confidence
claim. Its eight pair estimate and data-dependent admission can still amplify
noise. In particular green.30 and red.20 can occupy the same conjugate quad
frequency pair; shared weights cannot independently select incompatible depths
for those components. This is retained as a fixed adverse, not an automatic
claim that this or all spectral methods fail on the actual photograph.

## Actual consumer and root-run CLI

```text
python -B -X faulthandler stream.py --mode cost16 --out <fresh-output>
python -B -X faulthandler stream.py --mode source149 --out <fresh-output>
    --renderer-binding <executable.json> --development-receipt <held-development.json>
python -B -X faulthandler stream.py --mode full299 --out <fresh-output>
    --renderer-binding <executable.json> --development-receipt <held-development.json>
```

Only root may release each stage. `cost16` uses original grid indices
`[0,108,7848,7956,54,3924,4032,7902,1989,2016,2043,3951,4005,5913,5940,5967]`:
four corners, four edge midpoints, eight fixed interior sites. This selection
precedes any numerical outcome. It executes signal+all16 probes, actual
variance/admission/accumulation and actual finish/OLA. Initialization and one
entire-path warmup are reported separately. The timed batch includes geometry
and interpolation, not merely FFT calls. Partial candidate/uniform CFA and
coverage are saved, explicitly not photographic outputs.

`source149` and `full299` require all7957 patches and a native developer. The
streamer processes one unaligned source-u16 frame at a time, at most16 patches
per batch, retaining global complex weighted/uniform patch sums and real
weight sums. It does not retain an aligned source-image volume. Source149
exercises real analysis/fusion/synthesis, with no singleton-copy bypass.

Input identities are the frozen299 cache-export receipt, original order and
held map. Cache bytes and metadata are checked before/after for every consumed
source; all299 original RAW file metadata are checked. Original RAW bytes are
**not** reread by this worker: their byte identity comes from the retained
verified export. The export's independent decoder comparison did not cover the
extra four native columns; that limitation is carried in the receipt. Map
coefficients retain their stored bits, including the tiny nonidentity of149.
No CA profile or second spatial gather is applied to these original caches.

Complete arm files are `candidate/cfa-dn.f32le` and `uniform/cfa-dn.f32le`,
6896x4596 signed black-subtracted physical RGGB at origin68,46. Each receives
the same held development through `native-cfa-develop`, once, with receipts
under `<arm>/native/receipt.json`. The developer separately commissions its
held-CFA no-op before release. Full image presentation is a subsequent root/
photo-review step; a complete TIFF receipt is not itself photographic approval.

Successful streamer statuses are `COMPLETE_NATIVE_SPECTRAL_COST16`,
`COMPLETE_NATIVE_SPECTRAL_SOURCE149` and `COMPLETE_NATIVE_SPECTRAL_FULL299`.
All retain `quality_claim=false` and `photographic_admission=false`. A raised
support/nonfinite/binding/runtime error produces `INCOMPLETE_NATIVE_SPECTRAL`
and a nonzero exit. No numerical threshold, patch, noise approximation or
source population is changed automatically after any outcome.
