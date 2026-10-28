# One faithful performance opportunity

2026-10-27. Source/receipt audit only; no producer edits or jobs. The executed
producer remains378e42c1. No quality conclusion or speedup is claimed.

## Use the complete-source cost

The [complete source149 receipt](../../../../outputs/raw-quality-2026-10-27/native-spectral-source149-1/output/receipt.json)
records22.9376248s across all7957 patches,1.2226753s finish and34.8501769s worker
elapsed including both native developers and I/O. The root process completed
cleanly. Peak Torch allocated/reserved were5,509,941,760/6,650,068,992bytes.
All16 original-noise draws were consumed for every patch.

The earlier single16-patch batch took0.2554155s. Its extrapolation to roughly
127s/source was misleading: the warmup used a different batch shape, whereas
the complete source subsequently reused its plans. The authoritative299-source
**projection** is now approximately1.9hours of measured-batch-equivalent work,
plus initialization, source I/O, final synthesis/development and any changes in
actual load. This is not a measured299 run. It is already a plausible bounded
photographic diagnostic; speculative optimization need not postpone it.

## Smallest unchanged-operator optimization

Cache the16 noise fields in **original sensor coordinates** for the current
source. They require `16*7032*4688*4 = 2,109,849,600` bytes. Preserve the literal
existing `original_probe` and f32 signal/variance/square-root/multiply expression
when populating the cache. After reflection, `spectral_extract` reads the
cached value at the same original row-major index. Signal extraction continues
to read originalu16. Free the cache before replacing the current source.

This retains the source/draw/site identity, reflected/overlap reuse, all16
draws, every FFT shape/order, mean/taper, cell ratio, Lagrange evaluation,
pair-difference order, admission and source-fold order. It stores simulated
noise on the original sensor, not an aligned image or a decoded RGB volume.
No scalar variance, white-noise approximation or fewer probes substitutes for
the propagated floor.

Each patch currently extracts2*128^2+256^2=98,304 original lattice occurrences.
Across7957 patches this is about23.7 occurrences per original native site,
before the16 draws. Cached generation therefore eliminates substantial repeated
hash/log/cos/sqrt/variance work. It adds a f32 read per occurrence and a2.11GB
field initialization/write, so it is not automatically faster. The green
lattice's diagonal source access is also not contiguous. The existing peak
allocation plus this cache is nominally about7.62GB, inside the12GiB allowance;
actual overlapping lifetimes and reserved memory still require observation.

Crucially, no existing receipt apportions time by kernel. The other large work
remains: for each16-patch batch,17 three-lattice source FFTs,17 three-lattice
padded inverse FFTs (green1024x1024),17 four-phase analysis FFTs and68 launches
of the256-tap interpolation loop. Caching probes removes none of those. Calling
RNG the dominant bottleneck would be unsupported. Even a24x improvement in the
RNG portion halves total time only if that portion exceeds roughly52% of total.

## One short decision, then the photograph

If root selects the cache optimization, retain the current source and expose a
separate cached extraction path. Use the same fixed16 actual patches and
source149. First warm the **same16-patch shape** on each path. Time cache
initialization separately, then one like-for-like complete prepared batch with
all16 probes, accumulator and finish. Record CUDA-event stage durations for
noise generation/extraction versus FFT/evaluation if practical; do not infer a
whole-source gain from only the replaced kernel.

Require bit equality of the producing probe lattice samples, gathered probes,
Z, V, admission and delivered CFA on that fixed comparison, including reflection
and both greens. A changed compiler specialization may change f32 libdevice
results even with the same expression; if equality fails, preserve the failure
and do not silently widen a threshold. If the complete prepared path improves
materially including amortized cache initialization, one complete source149
replay is cheap enough to verify its actual cost and final payloads. Then root
can release the already-defined299 photograph. If it does not, use the existing
roughly1.9hour projection rather than launch a broad performance campaign.

Do not combine this with paired-probe differencing before the transform, rFFT,
new FFT batch layouts, a different interpolant or source-order changes. Those
may be algebraically related but alter f32 evaluation and would obscure this
single exact-cache discriminator.
