# Independent fixed spectral controls

2026-10-27. Prospective source protocol; no control has been executed. Root owns
all jobs. CLI: `controls.py --out FRESH --renderer-binding EXE_JSON
--development-receipt HELD_JSON`. Receipt: `COMPLETE_NATIVE_SPECTRAL_CONTROLS`,
`complete`, `controls_pass`, `quality_pass`, `quality_claim:false`,
`photographic_admission:false`. Mechanical errors/refusals remain distinct from
quality failures. No image-dependent thresholds, patch search or parameter sweep.

Four Torch CPU threads/one interop, CUDA f32/complex64, TF32/autocast off;
10GiB allocated/reserved ceiling, root300s/12GiB host. Independent reference
arithmetic alone is NumPy f64. No RAW decode or original-corpus load in controls.
Native delivery uses the new bound single-MHC developer and the actual held
development receipt; complete signed CFA and normalized camera RGB are retained.

## Mechanical commissioning

Constants/noisy flat acquisition precede detail scenes. Literal original RGGB
coordinates, independent native reflection and source-lattice extraction feed
a NumPy unitary FFT. Explicit signed even-Nyquist splitting, independent f64
cell-ratio evaluation and direct Fourier summation at selected output queries
are the approximation reference, not the producer's interpolation helper.
Use identity, fractional translation and a fixed1.10scale/0.12radian similarity.
The approximation bar is max0.06DN and RMS0.01DN at predeclared samples. Constant
gather and full OLA have max0.02DN error. Physical origin/pitch, wrong green
lattice and omitted cell response pass through producing diagnostic paths;
their errors must fail the same appropriate scorer. A separate continuous
cell-integrated Fourier truth records model/window error, not disguised exact
interpolation parity.

Original-coordinate probe reuse is checked across repeated, overlapping and
reflected sensels, reversed patch order and independent source IDs. A fixed
probe population checks normalized mean/variance (absolute mean<=0.04,
variance0.90..1.10), without fitting a new variance. Recompute one actual
16-draw marginal floor independently and require max normalized error<=2e-4.
Conjugacy, nonnegative finite variance/admission and actual source counts are
required. Uniform aggregation must equal direct synthesis of the mean gathered
patches: max0.06DN/RMS0.01DN. One-source must use actual analysis/synthesis;
there is no exact-copy bypass. Complete odd/even output coverage must be positive;
a missing boundary patch must be caught by the same coverage check.

## Fixed quality cases

Two independently acquired flat realizations, neutral structured, independent
RGB including8DN green, green0.30 inside the quincunx diamond, G0.30/R0.20
different-focus shared-bin conflict, red0.20/0.30 cancellation with a shifted
sharp companion, separable-frequency near-fine/far-coarse, and crossed
structures plus a glint under sign-changing symmetric blur. These are a fixed
small population, not a blur/threshold campaign. Acquisition noise is generated
independently from the supplied gain/read model before u16 rounding; rounding
is disclosed, not added again as another private noise model. All sources are
retained; no fitted source argmax is a truth reference.

Report complete candidate/uniform CFA, actual camera RGB, native RGB16/linear,
truth and per-component recovery. Fixed descriptive quality bars: flat RGB and
chroma error<=1.15 times uniform plus0.5DN; declared positive components recover
at least0.80 amplitude, with false-channel amplitude<=max(3DN,0.10*amplitude).
Adverses use the same reported bars without an automatic refusal guarantee.
No aggregate score can erase one lost color/depth component. These flags may
fail while `controls_pass` stays true; a root-authorized complete photograph
remains possible if hard mechanics and cost are sound.
The component recovery bar is a lower bound only: over-recovery can pass it.
It is not an overenhancement, ringing or halo guarantee. Complete output/error
and actual amplitudes remain visible for that judgment. The crossed Fourier
packets and synthetic disk response are not opaque-visibility or optical
calibration truth; the negative transfer is explicitly asserted and recorded.

## Frozen real-source149 cost population

Native output6896x4596, delivered origin(68,46). Local origins are
`x=-64,0,...,6848`, `y=-64,0,...,4544`, row-major109columns x73rows=7957patches.
Add delivered origin before applying the held map. The exact16 indices below
are fixed by geometry, not image content:

| Role | Grid column,row | Index | Local native origin x,y |
| --- | --- | --- | --- |
| top-left | 0,0 | 0 | -64,-64 |
| top-right | 108,0 | 108 | 6848,-64 |
| bottom-left | 0,72 | 7848 | -64,4544 |
| bottom-right | 108,72 | 7956 | 6848,4544 |
| top midpoint | 54,0 | 54 | 3392,-64 |
| left midpoint | 0,36 | 3924 | -64,2240 |
| right midpoint | 108,36 | 4032 | 6848,2240 |
| bottom midpoint | 54,72 | 7902 | 3392,4544 |
| interior | 27,18 | 1989 | 1664,1088 |
| interior | 54,18 | 2016 | 3392,1088 |
| interior | 81,18 | 2043 | 5120,1088 |
| interior | 27,36 | 3951 | 1664,2240 |
| interior | 81,36 | 4005 | 5120,2240 |
| interior | 27,54 | 5913 | 1664,3392 |
| interior | 54,54 | 5940 | 3392,3392 |
| interior | 81,54 | 5967 | 5120,3392 |

Cost must include original indexing/noise generation, all16 probes, all padded
FFTs, interpolation, floor, weighted/uniform accumulation and finish. Warmup,
bindings, current-source storage and transfers are separately reported. Small
batch extrapolation is a practical screen, not measured whole299 performance.
No actual cache pixels are read by this control protocol.
