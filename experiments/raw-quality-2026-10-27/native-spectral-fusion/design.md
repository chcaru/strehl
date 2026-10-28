# A native source-lattice spectral consumer

2026-10-27. **DERIVED proposal; UNVERIFIED implementation, cost and quality.**
No code, import, image calculation, RAW read or build was run for this audit.

## Decision

There is a bounded, materially different operator worth a small implementation
decision: construct a declared trigonometric interpolant on each original
sampling lattice, evaluate it at the consuming patch, and combine the resulting
four-component Fourier coefficients with one shared, noise-gated source weight.
This is interpolation plus fusion, not an optical inverse or new-resolution
claim. It does not require recovering target-grid Fourier coefficients from a
nonuniform Fourier projection. That latter shortcut is generally a coupled
Gram operator and is **not** selected here.

The critical implementation risk is cost: the complete consumer includes the
noise propagation, not just one FFT. Release a complete photograph only after
one actual full-source cost checkpoint. Do not substitute a cheap white-noise
floor or omit affine evaluation to make that checkpoint pass.

## Fixed proposed signal path

1. Retain original u16 RGGB sources and the existing held runtime map. Use f32
   signal, complex64 spectra and the established geometry precision. No source
   RGB, MHC, remosaic or source-u16 writeback occurs. Only the final four-site
   CFA image receives the ordinary single demosaic and pinned development.
2. Output patches are 128x128 native pixels, on a 64-native-pixel stride. Each
   has four 64x64 physical phase arrays. Centers and source-patch origins are
   fixed by the held pull map, never by sharpness or observed quality.
3. R and B use their pitch-two square lattices. Green uses the **combined**
   quincunx lattice, with integer coordinates
   `u=(x+y-1)/2, v=(x-y-1)/2`, hence `x=u+v+1, y=u-v`.
   Its Nyquist region is the native diamond `|fx|+|fy|<=0.5`, not either
   individual green phase's square. G1/G2 are later evaluations of this same
   green field at their distinct physical sites. They are correlated samples,
   not independent noise replicates.
4. Around each mapped patch center, use 128x128 R/B lattice samples and
   256x256 green lattice samples. Subtract each lattice patch's mean, multiply
   by a separable flat-top cosine taper, and FFT. The taper is one throughout
   the central 96 R/B or 192 green samples, with half-cosine transitions to
   zero over the remaining outer 16 or 32 samples on each side. Add the mean
   back after evaluation. Every requested source coordinate must lie inside
   that flat region with two lattice samples to spare; otherwise refuse the
   fixed geometry rather than change the patch. At the sensor boundary use
   explicitly recorded even reflection of integer native CFA coordinates;
   parity is preserved. Reflected occurrences reuse the **same** original
   sensel and noise draw. They do not create measurements or enter active-area
   noise statistics.
5. The interpolant represents the band-limited extension of source-cell
   averages. For a source physical mode `f` and reference-to-source linear map
   `A`, first split even-size Nyquist terms symmetrically between their signed
   frequencies, then multiply each signed-frequency coefficient by
   `sinc((A^T f).x)*sinc((A^T f).y)/(sinc(f.x)*sinc(f.y))` before evaluation.
   Here `sinc(t)=sin(pi*t)/(pi*t)`; the denominator is nonzero in these source
   Nyquist regions. This maps the **declared band-limited model's** source-cell
   integral to the reference unit-cell integral. It does not undo aliases,
   identify a PSF or make windowed non-band-limited scenes exact.
6. Evaluate this source-lattice trigonometric polynomial at each held affine
   pull coordinate. The practical fixed approximation is 4x Fourier
   zero-padding followed by centered, separable 16-node Lagrange evaluation
   on that oversampled lattice: for coordinate `m+t`, `m=floor(coordinate)`,
   use nodes `m-7` through `m+8` and the ordinary degree-15 cardinal Lagrange
   polynomials. All FFTs are unitary (`norm="ortho"`); the 4x-padded 2-D inverse
   is multiplied by four to preserve the original interpolant's amplitude.
   The preceding symmetric Nyquist split is retained in the padded spectrum,
   preserving real conjugacy. This approximation is commissioned against
   direct Fourier summation on small inputs; it is not called exact affine
   interpolation. Integer lattice identity and a translation evaluated by the
   direct Fourier reference distinguish interpolation error from the declared
   interpolant's own finite-window response. No linear/Catmull fallback.

These are four CFA-valued patches gathered inside the consumer, not an aligned
frame volume. The aperture ratio, taper, oversampled evaluator and boundary
reflection are all part of the measured transfer and its noise propagation.

## Fixed aggregation and noise semantics

Let `g[i,c]` be a gathered phase patch. Let `h` be the separable periodic Hann
window on the 64x64 quad grid and `s=sqrt(h)`. Subtract
`mu[i,c]=sum(s*g[i,c])/sum(s)`, then form
`Z[i,c]=FFT(s*(g[i,c]-mu[i,c]))`.

Propagate the **same injected original-sensel noise model** through the complete
linear path above, including mean subtraction and this FFT. Use the existing
eight independent probe pairs: sixteen deterministic original-sensel f32 draws
per source. Pair-difference squared complex coefficients divided by sixteen
estimate each marginal `V[i,c,k]`. The signal remains original u16; probe
values are signed f32. No residual-fitted variance, division by 299, or assumed
postmerge upper bound is introduced.

At each non-DC quad frequency, use

```text
E[i,k] = mean_c(|Z[i,c,k]|^2 / max(V[i,c,k], 1 DN^2))
F[i,k] = mean_c( V[i,c,k]    / max(V[i,c,k], 1 DN^2))
a[i,k] = max(E[i,k] - 2*F[i,k], 0)
w[i,k] = a[i,k]/sum_i(a[i,k]) if the sum is positive, else 1/N
Zhat[c,k] = sum_i(w[i,k]*Z[i,c,k])
```

The FFT normalization fixes the stated coefficient units. Enforce conjugate-pair
weight equality. Use the identical real weight for both complex components and
all four physical phase arrays. The weighted-mean subtraction makes DC zero
apart from roundoff; set it to zero and average `mu` uniformly. Reconstruct each
patch contribution as `h*mean_i(mu[i,c]) + s*IFFT(Zhat[c])`, then divide the
overlap-add image by its accumulated `h`. With uniform weights this reduces to
the mean of the **declared gathered patches**, including at image boundaries;
it does not reduce to the unavailable true image.

This is fixed noise-gated, power-two magnitude accumulation, not a calibrated
likelihood. It normalizes source weights separately at each frequency, so large
coarse-band energy cannot purchase arbitrarily more influence in a global
inverse objective. It retains different-depth frequency content more directly
than one full-value source weight. The four-component spectrum is a **polyphase
CFA representation**: its bins are not four independently observed common
physical frequencies. In particular, green diamond information appears in
phase relations that must remain intact.

Marginal variances suffice for the stated expected sum of squared normalized
components; they do not make phases, bins or overlapping patches independent.
Any reported output variance must account for their shared sensel rows. No
strict DC-estimator variance ceiling is imposed. The actual noisy-flat output
is the necessary tradeoff measurement. Strong glints can dominate admission;
retained saturated/working-limit codes remain censored observations, not
recovered highlight radiance, and the linear noise model does not explain that
censoring. This recipe has no automatic occlusion or saturation guarantee.

## Decisive limitations and the smallest release screen

The published [FBA paper](https://dev.ipol.im/~mdelbra/fba/FBA_cvpr2015_preprint.pdf)
combines registered RGB spectra by magnitude-derived weights for motion-blurred
bursts. Its common-image convolution assumption and its reported sharpness/noise
tradeoff motivate the accumulation only. Neither its RGB input path nor its
motion-blur results establish CFA sampling, focus-bracket or occlusion safety.
No external implementation source was consulted.

There is an exact adverse case even before code: a red-only continuous signal
`K + A*cos(2*pi*.20*x)/sinc(.20) - A*cos(2*pi*.30*x)/sinc(.30)` has constant
unit-cell measurements at red sites `x=2n`. Symmetric blur with different
responses at .20 and .30 exposes a nonconstant aliased signal. Spectral energy
can therefore prefer the blurrier source. A diverse-phase sharp companion
provides information but does not turn independent per-source interpolation
into joint alias resolution. Preserve this limitation explicitly.

A single fixed screen should run flats first, then only the following useful
mechanics/adverses: independent constant colors and noisy flats; integer and
fractional translation plus one nonunit similarity against direct Fourier
evaluation; physical green .30-native-frequency oblique detail inside its
diamond; independent R/B detail; the cancellation/diverse-phase pair above;
simultaneous near-fine/far-coarse structure; and a crossing/glint with
sign-changing defocus response. Preserve all finite outputs through the actual
single MHC writer. Uniform weights, wrong green lattice/phase, and omitted
aperture ratio must exercise the producing path. Quality failures remain
failures; mechanical source/phase/nonfinite failures block a photograph.

Finite windows can mix different depths at one frequency; complex averaging
can then cancel genuine structure. No magnitude rule can resolve arbitrary
occlusion or opposite phases. Finite source taper can also ring inside the
flat region. Passing constants or FFT roundtrip cannot dismiss either defect.

## Complete-image route and decision boundary

Process one original source at a time and bounded patches on the GPU. Retain
only global patch accumulators: weighted complex numerators, an unweighted
complex sum for zero-evidence fallback, real weight sums and mean sums. At
6896x4596, approximately 108x72 overlapping patches require about 1.02 GB per
four-phase complex accumulator and 0.13 GB per real weight accumulator, before
padding, current-source/probe scratch and final CFA. This is a storage
calculation, **not** a timing or device-memory measurement.

The 16-probe path entails millions of small FFT/evaluation operations over
299 sources. First measure one full native source including all probes and
finish overhead. If the bound is impractical, stop this fixed route; changing
the noise approximation is a new decision. If mechanics and cost justify a
photographic diagnostic, produce complete candidate and uniform outputs beside
the unchanged current native baseline, with the same map/crop/tone and all ten
fixed native witnesses. The uniform arm isolates the new interpolant from
spectral source admission. Neither arm fulfills a claim of improved geometry.

The negative precedents travel: [global inverse checkpoints](../direct-cfa-level-balanced/results.md),
[strict variance-cap obstruction](../joint-cfa-local-fit/identifiability/operator-proposal.md),
[full-value fusion](../native-pixel-fusion/photographic-review.md),
[shared-color guide failure](../../raw-quality-2026-10-26/insect-color/independent-results.md),
[complete dual-tree rejection](../dual-tree-cfa-gpu/photographic-observation/results.md),
[joint Lanczos](../../quality-september14/joint-cfa-lanczos-verdict.md), and the
original checkout's `experiments/native-cfa-kernel/results.md` (both positive
kernels softened the complete chip). This proposal changes the native lattice
interpolant and frequency-local fusion together; it does not declare their
previous photographic failures solved. The current
[incomplete blur-phase graphs](../insect-blur-phase/full/independent-actual-review.md)
also prevent substituting a supposedly improved alignment map.
