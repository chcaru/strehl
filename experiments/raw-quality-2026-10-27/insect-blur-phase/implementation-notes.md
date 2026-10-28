# Fixed original-green BIPC implementation

SOURCE-PREPARED2026-10-27. Root executes. No source-data, numerical, CUDA,
import or build job was run by the author. `phase.py` is independently written
from the mathematical operator named in brief.md; no external implementation
source was consulted. It is a reader, not a changed map or a quality claim.

## Callable interface

```text
noise = PhaseNoise(gain, read_variance, black=512., white=15360.)
reader = Reader(torch, device='cpu' or 'cuda')
reader.compare(reference_u16, moving_u16, noise,
    seed_native_xy=(0,0), phase='G1',
    reference_origin_native_xy=(1,0), moving_origin_native_xy=(1,0),
    return_surfaces=False) -> record
reader.compare_batch(reference_u16, moving_u16, noise, same_keywords) -> list[record]
reader.metadata() -> JSON dictionary
```

Singleton inputs are128x128; batch inputs are Bx128x128,1<=B<=32. Inputs may be
CPU/CUDA Torch uint16 tensors or NumPy uint16 arrays accepted by Torch; original
storage is never mutated. Arithmetic uses a copied f32 tensor, without WB,
interpolation, green-phase averaging or demosaicing. Pass a separate noise
instance if the supplied G1/G2 profile variances differ. No private fitted
variance, additional quantization term or source-count noise division exists.

`phase` is one physical RGGB green: G1 native parity(1,0), G2(0,1). Origins
must be finite integer original-active coordinates of that parity. Coordinates
may be a shared xy tuple or Bx2. Input pixels are sampled at origin+2*(x,y).
Seed is integer **patch-relative** displacement in native pixels, bounded to
absolute4096; it is not a native image coordinate. Both arms search residuals
+/-2 native pixels at1/64-pixel spacing. The convention is moving(x)=ref(x-d).
Returned `displacement_native_xy = moving_origin-reference_origin + d_patch`;
`patch_displacement_native_xy` and `residual_native_xy` are also retained.
All estimates are returned even if refused; use `accepted`, never existence
of a finite estimate, to identify supported local correspondences.

The ordinary spectrum is Fmoving*conj(Freference)/magnitude. Power2 uses its
complex square, not its magnitude square. The direct score is
`Re sum(weight*p**power*exp(+i*2*pi*power*f_native*d_patch))/sum(weight)`.
Thus the search variable already has correct displacement units: phase and
frequency are multiplied by power, rather than forgetting to halve a doubled
peak. Seed phase is reduced modulo256 native pixels for p1,128 for p2; the
reported seed is not reduced. These periods and the wrong-seed128 sentinel
make the unresolved global branch explicit. The reader does not certify the
caller-supplied branch or claim global shift identifiability.

## Fixed arithmetic and decision

Mean removal precedes a symmetric Hann window. Shared source FFTs, radial
band0.02<=frequency<0.20cycles/native, powers and weights feed both arms.
NoiseModel assigns `v=gain*max(raw-black,0)+read_variance`. Conditional on those
assigned variances, the noise of the exact demeaning/window row is propagated:
`N(k)=sum(v*w*w)-2*Re(conj(FFT(w))*FFT(v*w))/M+abs(FFT(w))^2*sum(v)/M^2`.
This accounts for the common subtracted mean. Shot variance evaluated at noisy
observations remains a model approximation; u16 rounding is not extra fitted
noise. Negative roundoff at removed DC is harmless, but nonpositive variance
inside the fixed band is an error. No statistics of scene structure are called
sensor noise.

The shared weight is the product across sources of
`max(P-N,0)/(max(P-N,0)+N)`. It is a data-dependent reliability heuristic,
not a calibrated likelihood. A common pair refuses if any sample is at0 or
at/above supplied working white, fewer than16 band bins exceed4N in both images,
effective weighted bin count is below32, or the weighted frequency second
moment's eigenvalue ratio is below0.01. Counts include conjugate bins and are
explicitly not independent observations.

The compatibility keys `CLIPPED_SOURCE`/`clipped_sample_count` mean this
configured working-limit admission only. The current15360 working white is
below the header16383 rail; this reader does not establish physical sensor
saturation, lost highlight information or the correct handling of those pixels.

Each power separately refuses a search-boundary peak, normalized score<0.20,
nonpositive minimum eigenvalue of negative score Hessian, or another3x3-local
maximum outside radius0.25native whose score trails by<=0.02. All failure
reasons are retained, together with the raw displacement, score, second peak,
curvature and shared support. These fixed thresholds precede execution and
must not be retuned from outcomes. They are not universal occlusion/asymmetric
blur rejection: indistinguishable PSF shift, changing depth or texture can
still pass. The independent controls assess such errors without relabeling
accepted correspondence as identified physical motion.

Records are JSON-serializable by default: `shared`, `p1`, `p2`, plus explicit
`physical_error_identified=false`. Each arm has `status`, `accepted`, `refusals`,
all three displacement forms and peak diagnostics. `return_surfaces=True`
additionally returns each complete257x257 score surface as a CPU f32 Tensor;
the caller must save/remove that tensor before JSON serialization. Malformed
shape/dtype/origin/model or nonfinite producing arithmetic raises an error;
scientific support/refusal is a complete record, not an exception.

## Bounded batching and later integration

Reader caches only the fixed window/frequency and two257x128 DFT matrices.
It computes batched source FFTs once; two separable complex matrix products
evaluate each local score surface, avoiding a bins-by-all-shifts cube. Source
patches are the only image input volume; no aligned frame volume is formed.
Peak search, alternative maxima and Hessians are batched too. One packed CPU
transfer for shared diagnostics and one per arm replaces per-record GPU scalar
reads; optional complete score surfaces transfer once per arm. Numerical
reductions remain f32; batching may change low-bit reduction order and is not
claimed bit-identical to a singleton backend before independent execution.
TF32/autocast are disabled/refused. No imports of Torch/NumPy occur in this
module; the caller supplies its pinned runtime and worker/resource limits.
No throughput or memory claim is made before root's bounded measurement.

The eventual graph caller can feed batches from original caches, preserve all
tile/pair statuses, and pass accepted physical observations to the existing
Rust pair/global solver. This source adds no geometry solver, stationary field,
three-site correction or source-map writer. The brief's controlled measured
curvature, adverse windows/depth/PSFs, per-frame gauge and complete-image
requirements remain prerequisites for any later map/render release.
