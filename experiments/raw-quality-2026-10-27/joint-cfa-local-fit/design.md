# Decision: close scalar-admission local fitting; test RAW band constraints

2026-10-27. Source/design only; no implementation or run. The selected small
question is whether **band-specific constraints on original photosites** can
retain different-depth coarse and fine content while jointly fitting sampling
phase. This is not an optical inverse, calibrated visibility model, new-resolution
claim or authorization for a full photograph yet.

## Why the proposed local polynomial is not selected

A quadratic fit would accumulate same-color original sample moments before
interpolation. Its six columns must integrate `[1,x,y,x*x,x*y,y*y]` over the
transformed original unit sensel: covariance is `A*A^T/12`, where A maps source
to reference. Its requested reference-cell value also contains the unit-cell
second moments, not just the intercept. Signed equivalent weights would be a
real difference from the rejected positive-kernel mean.

However, with repeated geometry, equal sample variances and one spatially
constant admission per source in the fitting window, every source has the same
normal matrix. The fitted polynomial is exactly the admitted weighted average
of the separately fitted polynomials. For two independently identifiable bands
whose source transfers are `(1,e)` and `(e,1)`, the two recovered coefficients
are `e+(1-e)*a` and `1-(1-e)*a`. Their sum is `1+e`, not2. No scalar `a` preserves
both when e is small. This restricted counterexample isolates the admission
problem from interpolation bias; it does not claim all spatially varying fits
reduce to this algebra. Variable admission can additionally create modulation.

The native-pixel trial already demonstrated severe same-channel near-fine /
far-coarse loss. Better signed spatial moments cannot by themselves supply the
missing source-frequency distinction. Splitting polynomial degrees is not a
solution: a Fourier component contributes to multiple degrees, and degree is
not an orthogonal physical frequency band. **Do not implement this full-value
quadratic recipe.**

## One fixed replacement discriminator

Use at most seven128x128 original-u16 CFA frames, known runtime similarities,
one injected phase-specific noise model, and one native-resolution continuous
camera-RGB latent field X with an8-native-pixel apron. Image math is f32.
Freeze the first maps to scale in[0.98,1.02], absolute rotation<=0.02radians,
and each native translation component<=0.75 about the panel center. Still
validate every actual footprint/Lanczos stencil before solving; the8-pixel
apron is not support for arbitrary maps. Refuse unsupported geometry without
changing crop or extending radiance. Output is the three reference-unit-cell integrals, developed directly once;
there is no final remosaic/MHC and no per-source RGB reconstruction or guide.

**A, the measurement operator.** For each original sensel, map its physical
unit-square footprint through the inverse source pull. Predict only its actual
spectral channel (both offset green phases refer to the same latent G field).
Reuse the independently authored normalized Lanczos3 evaluation and3x3
Gauss-Legendre source-footprint integration from `raw-blur-compatibility`, with
blur fixed to zero and no blur parameter. Do not reuse its72-pixel free apron,
Cauchy prior or nonlinear optimizer. Require full support; no boundary extension
or reference-pixel-then-warp substitution. Integrate the output reference cell
once with the same declared quadrature. X is continuous-basis coefficients,
not already sensor-integrated pixels. Independent continuous truth must expose
Lanczos/footprint approximation error.

**H, the source-space bands.** After A, unpack the original residual into four
physical CFA phases. Apply a complete orthonormal separable Haar pyramid to
each phase, at most seven levels, stopping when either extent is below2.
Pair transform is `(u+v)/sqrt(2),(u-v)/sqrt(2)` in f32; on an odd axis carry its
last low sample unchanged. Retain every detail and the final lowpass. The
128x128 CFA screen has64x64 phase planes and exactly six actual levels;
record resolved sizes, including odd-extent controls. This
specifies a complete transform without synthetic padded observations. H acts
on `A_i X-y_i`; it is not `A_i H X`. Separate G1/G2 filters retain their physical
positions through A, rather than pretending their centers coincide. Haar's
axis/shift dependence is a declared risk, not directional superiority.

**Fixed CFA admission.** Compute `d=H y` directly from black-subtracted original
samples. Propagate the injected per-sensel variance through the squared Haar
coefficients to obtain each coefficient's marginal V: both paired low/high
branches receive `(V0+V1)/2`, and an odd carried sample retains its variance.
Sibling/cross-band covariance is omitted from the surrogate, not assumed zero.
For every detail band,
E is the clamped-border3x3 mean of `d*d` and F the same mean of V. Fix
`a=max(1e-4, (max(E-2*F,0)/(64*max(F,1 DN^2)))^2)`; final lowpass has a=1.
No MHC, raw argmax, fitted focus plane, private noise estimate or source-index
selection enters. The1e-4 floor is an explicit numerical/admission choice,
not calibrated uncertainty. The source noise field is frozen from the supplied
model evaluated on the observed original signal; data dependence is disclosed.

**Objective and finite solver.** Fix
`J(X)=sum_i,b,k [a_i,b,k/max(V_i,b,k,1 DN^2)] * [H_b(A_i X-y_i)]_k^2 / N`,
where N counts original training sensels once. This is a weighted quadratic
surrogate, **not an independent-band likelihood**: heteroscedastic transformed
noise can correlate across bands. No fitted blur, image prior or output hull is
added in this discriminator. Freeze weights before solving. Use f32 matrix-free
CGLS from X=0, maximum64iterations, with no restarts or parameter sweep; record
true objective and normal residual every iteration. Numerical success requires
relative normal-residual norm <=1e-5 and finite nonincreasing objective; retain
the last finite image and explicit refusal if capped. Let `q=a/max(V,1)` and
`s=max(q)` over ALL training sources, phases and bands, after any test override.
Require finite positive s and use the ONE common metric scale in both producing
forward and transpose: `r=(sqrt(q)/sqrt(s))/sqrt(N)`. This avoids materializing
an underflowing `q/s/N`; every r must remain finite and positive or the solve
refuses its dynamic range. No per-band/source normalization or weight clamp is
introduced. The scaled objective is `J_scaled=sum ||r H(A X-y)||^2` and
`J=s*J_scaled`, with the same exact-arithmetic minimizer and relative normal
residual. Record s and both objectives; total-q=1 commissioning gives s=1.

Never form an unscaled f32 `dot(v,v)`. Reduce `sum((v/maxabs(v))^2)` in f32 and
retain the squared norm as a normalized f32 mantissa plus integer binary
exponent. CGLS alpha/beta and relative-normal-residual comparisons use ratios
of these pairs without reconstructing overflowing squares; objective reporting
also retains the pair if one f32 cannot represent it. Refuse nonfinite or
unrepresentable recurrence values. Handle an exactly zero initial normal
residual before any relative division or CGLS step. Minimum-norm/nullspace
behavior is an implicit choice, not measured radiance or identified detail.

For the small screen only, A may be sparse and retained. Its transpose and
H inverse must be the actual producing adjoints. Future full-image code may
not retain image-sized interpolation matrices for every source. No computation
of numerical solutions is authorized by this design alone.

## First falsifiers, in this order

1. Actual forward/adjoint dot products, constants and independent area-integrated
   Fourier scenes with nonunit scale/rotation. With the TOTAL multiplier
   `a/max(V,1)` explicitly overridden to1 through the actual objective seam,
   complete H must reduce to the same unweighted original-sensel squared error
   and gradient, rather than multiply evidence by the band count. One-sided
   phase/adjoint foils must fail those producing checks; the wrong-footprint
   foil must fail the physical node/area identity check even if its image error
   is below a noise-scaled adequacy bar for the small allowed maps.
   Merely setting a=1 under heteroscedastic V is not this Parseval null. Replace
   the old polynomial-exact/four-plane-MHC controls with actual A/H and direct
   RGB-cell delivery controls; do not silently inherit their different target.
   Exercise the actual high-DN Haar/admission path, an all-tiny common metric,
   an exactly zero initial normal residual and common-rescale invariance. The
   direct unscaled squared-norm foil must expose the overflow that scaling and
   stable reductions prevent; do not retune any image-quality threshold.
2. Neutral and independently colored flats with one frozen injected-noise draw;
   exact duplicated records cannot be described as independent evidence. Compare
   duplicate phases with genuinely independent noisy repeats and diverse phases.
   Missing channels and insufficient phase diversity retain explicit unsupported
   or ambiguous status, even when CGLS returns a finite image.
3. Same-channel near-fine/far-coarse continuous components first, with focused
   component witnesses, before attractive color-only cases. Compare the actual
   band weights with two causal foils on this and the alias case only. No-focus
   sets a=1 but retains each V denominator: it is a covariance-diagonal
   no-focus surrogate, not a raw whitened likelihood. Full-value computes one
   source scalar over ALL AC coefficients:
   `max(1e-4,(max(sum(d*d)-2*sum(V),0)/(64*max(sum(V),K*1 DN^2)))^2)`;
   apply it to all H coefficients including LL, retaining each V denominator.
   Neither foil is another candidate. No pooled RMSE may hide component loss.
4. The red-only sinc-compensated0.20/0.30cycles/native-pixel pair cancels on
   sharp red sites x=2n, while unequal defocus attenuation exposes aliased
   curvature. Add a genuinely diverse sharp-phase companion. This can reveal
   the RAW focus cue preferring blur or discarding informative sharp constraints;
   full rank alone is not admission. Retain independent color, weak8DN green,
   shifted geometry, glints and two-depth crossings. First scope refuses clipped
   observations explicitly; pretending clipping is ordinary Gaussian data or
   silently darkening it is not a fallback.

Independent control ownership remains with photo-review. All complete generated
fields and component/color/noise failures remain visible, including finite
iteration-cap outputs. Prediction residual alone cannot qualify the image.

## Actual prior boundary and full-image route

The September14 bilinear joint fit failed continuous signals; its Lanczos
replacement passed the signal screen yet made softened rails and cyan stipple
on the actual crop. Local geometry correction helped its MHC/Catmull comparator;
four RAW residual updates restored speckle without a missing feature. The
October16 full `native-cfa-kernel/operator.rs` uses positive radius1.5,
sigma0.30 kernels with one supplied focus/front and optional anisotropy; both
complete chip arms softened structures. Those are not this band-weighted
original-measurement objective. October27 counted/known-variance fits improved
component projections but still failed full RGB/chroma fidelity, so fixed known
blur or successful held prediction cannot discharge this screen. M83 corrects
Wronski's claimed >3dB advantage: it was15frames versus single-frame demosaicers,
not a paired CFA-versus-merge-then-demosaic proof. No external implementation
was consulted or paper result borrowed as a quality expectation.

If the fixed discriminator is useful, the faithful full-image route retains
one latent RGB field and a fixed number of f32 CGLS vectors, streams original
u16 sources, computes raw Haar guidance and A/A-transpose per source, and uses
the ordinary direct camera-RGB developer with pinned tone/matrix/ICC. No source
RGB or aligned volume is introduced. Generated small sparse matrices must be
replaced by on-demand tiled stencils with the same arithmetic and tested
adjoint. Output tiles need source footprints plus H support, not a guessed crop.

This is **not yet a practical full299 implementation**:64iterations require
many original-source passes, per-source weight regeneration or a potentially
large cache, and source-coordinate band support across tiles. Whole64-step
memory/cost cannot be inferred from one forward call. A later root allocation
must first measure one full-size source forward/adjoint/guide plus iteration
workspace, then price the exact source/pass count. Original u16 caches may avoid
redecoding; they are not free memory and must be explicitly budgeted. Clipped
data handling and a contract-correct complete-output fallback also remain open.
No full flat/weevil render is released until those are concrete. Neither the
old local-fit obstruction nor this design establishes an optical/capture ceiling.
