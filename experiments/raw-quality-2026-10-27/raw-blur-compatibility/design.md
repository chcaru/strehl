# Anchor-resolution original-CFA blur compatibility

2026-10-27. **ARGUED proposal; no implementation, RAW read, fit or photographic
claim.** This is separate from the coefficient-consistency CG restart. Test one
single-surface observation model before attempting another source selector or
general layered inverse. A successful flat photograph would be a useful first
consumer result, not admission on insects or an occlusion-halo repair.

## What the actual prior results change

- `quality-september14/joint-cfa-{decision,verdict,lanczos-verdict}.md`: the
  Lanczos forward basis repaired the fixed continuous-signal errors of bilinear
  reconstruction. It still amplified flat chroma noise versus the same-data
  mean. `joint-{photographic,local-photographic}-verdict.md` records thicker
  rails and periodic cyan/blue stipple on actual original-CFA chip patches,
  including after useful local placement corrections. Merely repeating a
  common-focus least-squares photosite inverse is not a changed question.
- `chip-differential-blur/{results,resampling-audit}.md`: the translation-only
  plant failed the zero-blur gate; a source-side interpolator and an unresampled
  target had different transfer. Do not estimate blur by resampling one observed
  image toward another or subtract a fitted numerical blur constant.
- `relative-blur-evidence/results.md`: the generated Gaussian discriminator
  passed, but actual facet/dark/nearby fits did not establish useful source
  ownership. Model support limits and asymmetric/chromatic/visibility mismatch
  remain real limitations. A Gaussian family is a hypothesis, not known optics.
- Original-checkout `marigold-joint-blur-placement/results.md`: a transformed
  source112 template could improve part of the lower core while missing farther
  strands and worsening every held background. Here the latent radiance is
  estimated from all observations, rather than copied from one source.
- `layered-raw-inverse/{in-focus,free-visibility}-results.md`: known-visibility
  matrix-prior reconstruction had conditional generated success, but free alpha
  failed image/flat requirements despite good held RAW prediction. Original
  `marigold-constrained-raw/results.md` then showed CFA-frequency lattice leaking
  into free alpha on the photograph. This proposal has no alpha variable.
- The current ribbon result is a conditional positive for two constant-colour
  capsules, not general spatial radiance or automatic topology. The saved-alpha
  perturbation did not reach its intervention: its recorded constant-response
  error was 0.041748 DN against 0.02 DN. Neither is a completed photo repair.

## One fixed changed operator

For a supported, non-occluding surface region, let X be one native-resolution
camera-linear RGB field in signal DN, containing the anchor exposure's unknown
in-focus optical response but preceding sensor-cell integration. For original
sensel q in source i, predict

    mu_iq = black_iq + S_iq [ G(v_i) * X ]

S integrates a unit square in ORIGINAL source coordinates, maps its quadrature
points through the held geometry and channel-dependent CA, evaluates a Lanczos3
continuous representation of X, and reads the literal sensel's channel. Thus
scale changes do not silently hold the footprint fixed in reference pixels.
The initial square uniform footprint is an explicit model assumption, not Sony
microlens calibration. S does not interpolate an observed source raster. G is
a normalized isotropic Gaussian,
shared across RGB; v_i is variance in native-pixel squared units. Set v_anchor=0
and constrain other v_i to [0,256]. A ceiling hit is unsupported, not a measured
16-pixel PSF. Deliver the reference unit-cell average of X, not the pre-integration
field. No second footprint filter is applied. Independent dense quadrature must
test both observation and output integration, including changed source scale.

Fit X and the scalar v_i jointly, using original u16 observations and the injected
per-phase sensor noise likelihood. Do not fit gains, translations, noise, pupil,
depth or coverage. Do not add a focus-energy admission weight. Known clipping
needs its actual sensor-code authority and censored likelihood; otherwise a
clipped region refuses this first model. Use the retained matrix-Cauchy spatial
prior, with its original DN/noise scale and coefficient, as one fixed baseline
regularizer. Its weak-colour crossing failure mode remains an explicit test;
the prior is not optical evidence or guaranteed colour protection.

This changes the common-focus assumption of the old Lanczos inverse: blurred
sources constrain G(v_i)*X rather than being forced to equal X. All frames use
one observation forward operator, avoiding the differential-blur sampling
asymmetry. Pinning the anchor to zero is valid for this nonnegative relative-blur
family only if that exposure is least blurred throughout the supported region.
Source30's useful contours do NOT establish that condition across the photograph.
It is a hypothesis to challenge on disjoint field cells, not an established gauge
choice. A sharper-than-anchor observation, or a change of least-blurred source
across the field, must cause refusal; do not silently select a replacement anchor
or permit negative variance. Nor is a real defocus stack known to obey a Gaussian
semigroup. X is an anchor-resolution output, not a pinhole image or
super-resolution claim. Poorly supported frequencies and blur parameters remain
unidentified; an optimizer return is not identification.

## Earliest bounded falsifier

Use one independently generated native-CFA test panel, at most 128x128 scored
support with an explicit additional latent/observation apron, and seven views.
Five views fit X and their variances. Freeze X, then fit each remaining view's
single variance using only predefined training spatial cells. Predict disjoint
cells of those two views. This is spatial/feature transfer conditional on X and
per-view calibration, NOT prediction at unseen focus without observations.
Held pixel values cannot enter radiance, variance, stopping or initialization.
Generate continuous textured fields with analytic Fourier attenuation
and direct sensel integration, not the solver's Lanczos/Gaussian raster code.
Freeze geometry, inputs, priors and stopping before execution. Save every
complete generated RGB field and parameters before applying assertions.

1. Flat first: noisy neutral and independent constant-colour cases, plus zero
   blur/translation identity. Before unknown fitting, include zero optical blur
   with known nonunit scale and rotation and independently integrated ORIGINAL
   source sensels. The model must not absorb changed pixel aperture into fitted
   variance. An intentionally reference-integrated-then-warped foil must expose
   the difference. Flat blur parameters must be labelled ambiguous;
   they cannot establish a direction or calibrate their own noise. Compare image
   error with the matched original-sample mean and actual canonical consumer.
2. Positive: genuinely coloured and neutral thin structures on one surface,
   unknown radiance and relative blur, with independently chosen fractional
   source phases. Compare delivered RGB/chroma and separate component retention,
   not gradient energy. Wrong CFA phase and wrong map must be live destroyers.
3. Decisive adverse: near fine and far coarse structures in one support, plus
   a brightness-changing glint and an asymmetric/chromatic blur mismatch. The
   single-surface model must either preserve both components or refuse on held
   spatial/feature evidence. Also include a source sharper than the pinned
   anchor and a field whose least-blurred source changes between cells.
   Report an accepted-but-erased component as failure
   even when total residual falls. Include the old missed-far-component pattern.

The key decision is whether this operator can distinguish compatible defocus
from mixed-depth/illumination mismatch while improving delivered colour/detail.
A matching Gaussian plant alone is insufficient. If an adverse case fits the
held data while deleting structure, stop: no threshold, kernel or prior sweep.
Numerical nonconvergence is reported separately from model rejection. Flat noise
and phase stipple guards from the earlier joint-CFA tests must not be omitted.

## Fixed first implementation contract

Reuse `joint-cfa-lanczos.py::_axis_weights`, the phase-selected
`layered-raw-inverse/model.py::observation_nll` formula, and the pure
`matrix-cauchy-prior.py::image_matrix_cauchy_dn` prior. Reuse the matrix driver's
one-source-at-a-time backward accumulation and contiguous-gradient repair, not
its pupil/alpha forward or continuation. New work is limited to Torch separable
Gaussian convolution and the original-footprint Lanczos forward/adjoint. Use
fixed Gaussian support radius64; v=0 is literal identity, otherwise normalize
exp(-k*k/(2*v)) on that support. Discrete small-variance approximation must pass
the independent continuous controls rather than receive a fitted correction.

All image/objective/gradient arithmetic is f32, TF32 disabled. Geometry can be
prepared in f64 before fixed f32 query weights. The sole injected model is
V_c=a_c*max(mu-black_c,0)+r_c+1/12 DN squared. Objective is the mean per-view,
per-eligible-sensel NLL plus one matrix-Cauchy prior, coefficient1. Before any
execution, root and independent review changed its normalization to the SUM of
all latent-field edge losses divided by OBSERVED output area. This prevents a
larger free apron from diluting the central prior; it is not an exact replay of
the historical whole-field mean prior. The physical-DN edge formula is unchanged.
Its b=sqrt(2*(mean(a_G1,a_G2)*2048+mean(r_G1,r_G2)+1/12)) DN reduces to the retained
scale for equal phase coefficients. No private noise, flux/alpha penalty or
channel-loss normalization is added. WB and display transformations stay outside
the fit. Initial X is the anchor's fixed normalized CFA interpolation, represented
as D*softplus(z), where D is the supplied digital-saturation-minus-black range.
Each non-anchor v starts at1 and uses256*sigmoid(theta); anchor v is exact0.

One Torch L-BFGS call: lr1, history10, strong-Wolfe, max_iter64, max_eval150,
gradient1e-6, change1e-11, hard160 total complete objective/gradient evaluations
including initial/final records. No restart or truth-selected iterate. Each
calibration view gets at most32 scalar evaluations with X fixed. Save numerical
limit/refusal status; a returned image does not imply convergence. Root's first
job ceiling is120s/4GiB; no automatic continuation follows a limit.

Minimal seams for independent controls:

    forward(x_rgb_dn_f32, variance_f32, query) -> predicted_dn_f32
    fit(train_views, calibration_views, config) -> FitResult
    predict(result, view_queries) -> predicted_dn_f32
    deliver(result) -> reference-cell-integrated_rgb_dn_f32

Queries carry original xy/CFA phase/black and mapped3x3 Gauss-Legendre footprint
nodes/weights. Codes remain u16. Pass explicit training/calibration indices;
score codes never enter fit. Config binds injected noise, anchor, native extent,
apron and fixed budget. Results retain X, delivered RGB, v, per-view support,
complete objective/gradient trace, bound/unsupported statuses and source hashes.
The independent generator uses different dense footprint integration and analytic
continuous blur, never forward(). This tiny Python prototype caches seven sparse
query matrices and one output matrix; only its backward graphs stream. It does
NOT implement production stencil streaming. A full-image consumer must prepare
stencils per source/tile and discard, rather than materialize all source tables.
Its sole latent includes a72-pixel free apron initialized by anchor replication.
Direct query support is reported without a prior-only/observability claim:
Gaussian blur can couple the apron to observations, including central scores.
The full observed output domain is saved, regardless of the control's score mask.
`integrate_reference(X, config)` additionally commissions known-X output
integration; `deliver(result)` returns the saved integrated output. This contract
is design only, not implementation authorization or executed evidence.

## Practical complete-photograph path and limits

Only after that screen, the first photo is the complete 60-source flat stack,
with existing source30 as a declared resolution anchor, fixed map/CA-on, first
source WB and exact saved display transform. Estimate the 59 shared relative
variances jointly on a fixed spatial grid with held grid cells, then condition
the whole-image reconstruction on those values. This global single-surface fit
is deliberate: do not invent a different blur or source distribution at every
pixel. Source30 remains only the prospective least-blurred hypothesis. A
disagreement across held cells, a sharper source, or incompatible field ordering
refuses the planar model rather than changing anchors.

Stream one original source at a time. GPU Gaussian convolution and literal
forward/adjoint queries retain O(image) f32 latent/gradient state, original u16
storage and small per-source parameters, with no aligned-frame or RGB-source
volume. Use bounded tiles with sufficient blur and Lanczos aprons if full-image
workspace is excessive; central values must pass a tiled/untiled equality check.
There is no supported runtime estimate yet. Commission one full-size forward/
adjoint and one fixed linearized iteration before committing the complete solve;
record allocation and extrapolate actual passes against a root-approved budget.
All60 full originals occupy approximately4GB of host memory, separate from GPU
workspace; every repeated source pass/transfer enters the cost projection.
Repeated RAW decoding per iteration is unacceptable; retain original u16 sources
in host storage/cache and transfer only the source currently consumed.

Deliver the final reference-cell-integrated X through the ordinary matrix/tone/ICC path,
without remosaic/MHC. Include complete RGB16 and float masters, the unchanged
canonical output, source30 control and existing full Helicon workflow results.
Compact source contours without purple interiors are the photographic objective;
lower prediction error alone earns nothing. A complete failure closes this
recipe, not joint reconstruction as a family.

There is no ready automatic insect adapter in this design. Extending to curved
surfaces requires supported local focus/blur variation; boundaries require
visibility and multiple genuine depths. A hard patch-selection mosaic would
reintroduce the source discontinuities just rejected. Do not hide that missing
step behind a generic coherence gate or claim that the planar test is a general
stacker. If the controls or full flat do not show a substantial gain, do not
build that larger machinery.

## Lookup record

Read-only searches executed for this design:

    python scripts/research.py search 'relative blur' 'joint CFA' --any --limit 4
    python experiments/ORCH-drift-check/prior_art.py gaussian relative blur latent

The required returned closures were checked: M78 shows that blur equalization
can improve conservation without prediction; M164 rejects output-only noise/
sharpness attribution; V-ORACLE is an older flowers capture-gap finding, not a
ceiling for these source-supported flat features. The September19
`raw-affinity-support/next-inverse-audit.md` is historical motivation, superseded
for execution claims by the actual joint/layered/marigold results above.

Published joint RAW reconstruction and occlusion-aware defocus work motivates
testing an observation model, but supplies no Sony kernel or current photographic
admission: [FocusDeep](https://arxiv.org/html/2311.17846v1),
[Ikoma et al.](https://www.computationalimaging.org/wp-content/uploads/2021/04/DeepDfD_ICCP2021.pdf).
No external implementation source was consulted.
