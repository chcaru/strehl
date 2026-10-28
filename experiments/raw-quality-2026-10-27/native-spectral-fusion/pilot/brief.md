# Fixed native spectral pilot

2026-10-27. Root releases implementation of the operator in ../design.md with
the objections in ../challenge.md retained. This is an unproven native RAW
candidate, not a PSF estimator or superresolution claim. No product default
changes. Source-only implementation initially; root alone releases jobs below.

Cfa-residual owns operator.py, optional local CUDA source, API/source notes and
the streamed complete-source/full-stack driver. Integration-review owns independent
controls.py, protocol, source challenge and receipt/conclusion review. Photo-review
owns a new standalone native CFA final developer source and its display adapter.
Root owns wrappers, scheduling, build registration and photographic judgment.
Never edit predecessor sources. New Rust files stay unregistered until root can
build them without disturbing an active other job's bound files.

## Frozen operator and interfaces

Retain128-native patches/64-native stride, R/B128-lattice and G256-lattice
patches, prescribed flat-top taper, cell-response ratio, fourfold FFT padding,
16-node separable evaluation,16 original-noise draws and stated shared polyphase
weights. No optical blur inverse or aligned-frame volume. u16 source storage,
f32 arithmetic, complex64, TF32/autocast off. Last output is CFA followed by one
native MHC/development, not per-source demosaic/remosaic. Document FFT normalization
and coefficient units before execution, including the1DN-squared variance floor.

Use physical source coordinates for probe identity and reuse the identical draw
for reflected/repeated sensels, both greens and overlapping patches. Unit-cell
integration and actual source-to/reference pull semantics must be explicit.
Specify even-Nyquist splitting, origin/tie convention and real conjugacy. Enumerate
patches from a negative half-window start through the last output support so Hann
coverage is positive at every delivered pixel; test corner/odd-edge coverage.
Reference149 and existing held map are unchanged; no phase-candidate maps.

Actual input uses originalu16 caches with their verified export identities and
before/after hashes, original metadata and held map/order. No fresh RAW decode
is needed. Retain exact active area, note the prior independent decoder's4-column
edge coverage limit, and do not call reflection new data. Compute no private
stage noise estimate. The injected Sony model and all conditional probe limits
remain explicit.

The operator must expose small-control gather/aggregate/overlap-add operations
without hidden full-source allocation, and a fixed-small-batch cost mode before
complete-source processing. API/source notes must let independent controls call
the very same path. All refusal/finite output states and failures are saved.

## Staged execution limits and decisive evidence

After source/API review root can run one controls job300s/1200CPU/12GiBhost/
10GiBGPU. Flats run first, followed by direct-Fourier row/translation/affine
oracles, physical-phase/pitch/omitted-cell-ratio foils, exact uniform-mean OLA,
independent color, green0.30 inside the diamond, the G0.30/R0.20 shared-bin
different-depth conflict, red cancellation/diverse phases, separable-frequency
near-fine/far-coarse positive and a crossing/glint/sign-changing-blur adverse.
Use independent observations and fixed display, not the producer's own fitted
model as ground truth. Preserve final CFA and native RGB for all cases.

Hard geometry/nonfinite/source-identity/constant/operator-null failures block a
photograph. Known color/noise/occlusion quality failures remain reported and
preclude default admission, but do not automatically prohibit one finite actual
photographic discriminator when mechanics/cost are sound. This is prospectively
declared: actual photographs are the decisive quality benchmark, and no synthetic
score or local crop completes the goal. No post-outcome threshold sweep.

Next root can release one fixed16-patch real-source149 cost batch spanning four
corners, four edge midpoints and eight fixed interior positions. Include the
entire16-probe, interpolation, FFT, variance, weighted/uniform accumulation and
finish path, plus warmup cost separately; no FFT-only extrapolation. Bound180s/
720CPU/12GiBhost/10GiBGPU. Exact patch indices freeze in protocol before running.
If extrapolation is plainly impractical, stop before a complete source. Otherwise
one complete source149 checkpoint is bounded300s/1200CPU/16GiBhost/12GiBGPU.

Root sets a full299 budget only after those actual costs. Complete output is
6896x4596 at native origin68,46 with the same held tone/ICC/WB/matrix. Provide
candidate and uniform complete masters alongside unchanged native baseline and
full HeliconB4/B8 context; inspect all ten frozen384px witnesses and preserve
every regression. The developer's no-op replay of the held CFA must exactly
reproduce current baseline RGB16/linear/material data. Candidate outputs save
signed CFA plus genuine final camera RGB, never inverse-developed estimates.
Only a substantial complete photographic gain justifies bug2/flat60 transfer;
broader flower/mineral/corpus acceptance and practical workflow cost remain open.
