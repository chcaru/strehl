# Small known-scene production benchmark: proposed forward-model scope

2026-09-07; root-requested bounded design audit. **No benchmark was run, no
milestone is allocated, and no product, M25 source, capture or holdout was
changed.** Source descriptions are **VERIFIED BY READING**; equations are
**DERIVED**; all selected parameters and next actions are **PROPOSED / UNRUN**.
This is an implementation brief to preregister and independently commission,
not an acceptance result.

## Recommendation

Use M194's existing decoded-CFA seam for a small, explicitly synthetic test of
the production Pyramid gather, fold and TIFF writer. Reuse **scalar-radiance M25
layers**, with fixed channel multipliers and no chromatic diffraction, for the
first focus/geometry experiment. Add a separate analytic RGB control, adapted
from the BUILD-DEMOSAIC design and evaluated independently at continuous
coordinates. **A general three-channel M25 extension is not necessary for this
first developer benchmark.** It is necessary before claiming spatially varying
chromatic defocus/occlusion performance, which remains unmeasured here.

The first useful result is a vector of reconstruction errors and temporal
variances under a commissioned numerical model. It can detect a broken crop,
misplaced frame, lost texture, color substitution or noise-coupled selection and
compare one admission change against a pinned production baseline. It cannot
certify the actual camera PSF, real occlusion-halo behavior, restoration quality,
physical depth or SOTA. Do not require those broader claims before measuring
software error on a scene whose inputs and references are known.

Use four small fixtures, each with a distinct purpose: flat, single textured
plane, two scalar layers with a slanted boundary, and independent analytic color.
Their controls come before any candidate comparison. Freeze parameters and
validity masks before generating candidate outputs. Do not tune the scene until
a favored algorithm wins, or replace a failed fixture without retaining it.

**First implementation is smaller than the complete design below:** implement
flat + single plane + analytic color, a fixed finite control set, and one pinned
production baseline. Add the two-layer output as a separately labelled diagnostic
once its alpha/order controls are ready. Do not hold those first software-error
results for a general physical-optics validation project. A failed numerical
optics check withholds its dependent optical-reference claim; it does not erase
successful flat/noise, coordinate, parity or known-color software controls.

## Evidence that determines this scope

- **M25 report §§0, 4.3 and 4.4:** noise/selection tests survived several
  challenges, but Gate 2 did not detect deletion of diffraction even though the
  images changed substantially. The simulated occlusion enrichment had the
  opposite sign from the real observation (truth-gated 0.23x), so its physical
  occlusion-reconstruction and PSF claims are not validated. Its model is still
  a precisely specified software stimulus. Existing scalar constant-depth
  layers avoid its additional approximate spatial-depth-band interpolation.
- **Producer API audit and independent check:** `scene.py::Layer` advertises
  `(H,W,3)` radiance; `render.py::similarity_warp` returns identity arrays before
  `h,w=img.shape`, then fails on nonidentity RGB. The independent 17x26
  translation/rotation controls confirmed this, preserving M25 sources.
  `channels="rgb"` uses one scalar radiance with `channel_scale`, not arbitrary
  spatial RGB radiance. Do not paper over that distinction.
- **BUILD-BLEND, “synthetic two-layer ground truth”:** the scene still
  under-produced the real rim defect after three stimulus repairs. The report
  withdraws its edge rows as evidence and says they are withheld. The actual
  `blend-truth.rs::run_scene` prints those rows first, then prints
  `SCENE NOT COMMISSIONED`, and returns `Ok(())`; process success does not enforce
  the report's admissibility restriction. Its nearest-depth selector
  was worse than the merges at the boundary, so a depth oracle is not a universal
  attainable floor. Its texture result survives only within its own scope.
- **BUILD-DEMOSAIC §§2–3:** continuous band-limited RGB scenes, real production
  gathers, parity/CA checks, known added chroma and an available true-chroma
  control already establish an appropriate component test design. A bilinear
  “destroyer” improved RMSE on a noisy smooth target and was correctly withdrawn
  as a defect control. Do not require every blur to worsen every noisy RMSE.
- **M103 §16:** endpoint placement is not the merge's per-frame input. The
  published independent 39-rung scale track departs its chord by 46.1 plane px
  at frame 200 in the original gauge. Reuse its dimensionless curved sequence,
  not a new linear ladder presented as real breathing. A synthetic plant using
  those numbers is not another independent measurement of the old capture.
- **M48 / M72 / M90:** M25 defaults include obsolete high-gain read noise,
  independence is not a complete physical sensor model, and fixed pattern is
  not temporal variance. Use deliberately specified synthetic coefficients,
  inject them once, and state the excluded fixed/correlated terms. This validates
  arithmetic and an operator, not camera calibration.
- **M84b / M135 / M166:** real focus-axis nonlinearity and reference-path limits
  remain relevant to later physical validation. A physical reference measures
  its qualified path, not unconstrained latent object truth. The synthetic
  benchmark must likewise name which reference each error uses.

The prior-art query also returned F-camera-lens-optics and M136's ground-truth
census. Their local reports were checked for relevant scope; neither commissions
this proposed forward model. No external implementation or GPL/LGPL source was
opened. No additional general metric search is recommended.

## Exact initial fixture and product settings

All coordinates below are **native active sensor pixel centres**: `(0,0)` is the
top-left RGGB R site. Array rows are y; all rectangles are half-open. Sensor size
is **320x240**, so the production full quad plane is **160x120**. Use nonzero
decoded-buffer active origin `(2,4)` with poisoned padding, following M194's
existing source test; the physical scene remains in active-area coordinates.

| Item | Proposed fixed value |
|---|---|
| Focus frames | 9; focus positions `0,1,...,8`, dimensionless index only |
| Latent grid | Supersampling S=4; 48 native px margin per side; midpoint quadrature within sensor cells |
| Synthetic optics | `Optics(n_marked=8, magnification=1, pupil_ratio=1)`, hence `N_eff=16`; 535 nm for every channel; pitch 5.12 micrometres; circular diffraction OTF times uniform-disc defocus OTF; no rig-fidelity claim |
| Defocus | CoC **diameter** 1.5 native px per focus-index separation; per-layer constant focus; negative OTF lobes retained |
| Sensor | `black=512`, `white=15360`, synthetic ISO label160, gain **0.25 DN/electron**, read noise **4 electrons**; RGGB; no FPN, hot pixels, PRNU or covariance |
| M25 construction | Explicit `Sensor(gain_divisor=640, base_iso=100, read_noise_e_low=4, read_noise_e_high=4, width=320,height=240,...)`; no default calibration is silently inherited |
| Channels | `channels="rgb"`, `channel_scale=(0.75,1,0.60)`, `chromatic_diffraction=False`; fixed as-shot gains `(4/3,1,5/3)` to return these fixed-color scenes to an achromatic output |
| Geometry | Exact nine-rung curved scale series below; zero rotation/translation in the first focus fixture; off-centre physical scale centre `(183,101)` |
| Photometry | All frame exposure gains1; no auto exposure, tone or fitted brightness normalization |
| Production | `Pyramid`, gate2, Catmull-Rom, full-resolution gather, native demosaic, CameraLinear output, unity commanded exposure; CA/defect/restoration off; retain every other resolved merge parameter in the manifest |
| Pyramid depth | Explicit **3 Laplacian bands** plus base, suitable for this small image; record actual `level_sizes`. This is the existing production implementation at a supported setting, not a default-seven-band performance/quality claim |
| Workers | 2 maximum; isolated worker/cache/temp/output controls; no timing or host-performance claim |
| Coverage | Use the actual `cover_or_explain(..., Crop)` and `pyramid_domain` on known placements; save the resulting crop before producing TIFF pixels. Same map/domain for every scene/noise repeat and single-frame comparison |
| Main score window | Fixed canonical rectangle `x in [64,256), y in [64,176)`; require every selected centre and interpolation support to survive actual Crop, otherwise refuse the planned window rather than move it |

These numerical values are test conditions, not measured properties of a rig.
Construct one `NoiseModel` from the explicit manifest's gain/read/level values and
inject it through `PreparedPyramid.noise`. Do not call `noise_model_for` with a
made-up camera and let its fallback coefficients replace the specified model.
Use the existing `Provenance::Fallback` enum with an explicit synthetic-known-
coefficient receipt, rather than falsely marking simulated constants `Measured`.
The enum is not a synthetic provenance vocabulary; no public enum change is
needed to commission the private test path. Noiseless controls keep the same
product configuration and injected model; only the input noise is disabled.

### Four scenes

Use `c(fx,fy,p)=cos(2*pi*(fx*x+fy*y)+p)` on the declared latent coordinate grid.
Radiance is in electrons before fixed channel multipliers. Extend the same
analytic functions through the margin; do not tile a small random crop.

1. **Flat:** one opaque layer, radiance12000, focus4. This is evaluated first.
   Texture-dependent registration is not run; known geometry is supplied.
2. **Single plane:** one opaque layer, focus4,
   `R=12000 + 1800*c(1/16,1/24,.2) + 900*c(1/8,-1/16,1.1)`.
   This provides real scene structure at several orientations, a best-focus
   frame exactly at the reference geometry, and an analytically computable
   in-focus observation target. These rational wave periods fit both proposed
   unwarped margin grids, avoiding an incidental periodic-FFT seam in the
   identity optical control. No focus-window optimum is inferred from it.
3. **Two layers:** opaque background with the same radiance as scene2 and
   focus6; foreground focus2 with
   `R=15000 + 1400*c(.045,.095,.7) + 700*c(.17,.01,.3)` and alpha1 where
   `x >= 160 + .15*(y-120)`, otherwise0. Supersampled alpha is a specified
   geometric half-plane; fractional pixel coverage comes from integration and
   blurred alpha. No stochastic texture map determines the scored boundary.
4. **Analytic color component control:** no M25 layer/channel extension. At
   every continuous coordinate use `R=L+C`, `G=L+Q`, `B=L-C`, in desired
   white-balanced black-subtracted DN, with
   `L=3000+450*c(.08,.03,.2)+180*c(.19,-.07,1.1)`,
   `C=240*c(.11,.04,.8)`, `Q=120*c(.05,-.09,2.0)`.
   Integrate each wave over sensor cells analytically, divide by the declared
   WB gain before RGGB sampling, and quantize once. Include `C=Q=0` as the
   achromatic null. Frequencies remain inside R/B's axis Nyquist for genuine
   color. Render on the same curved geometry; add a separately labelled
   translation/rotation case only in component commissioning, not as a claim
   that M25 supports a per-frame rotation series.

For scene3, freeze signed distance
`d=(x-160-.15*(y-120))/sqrt(1+.15^2)`. Report separate masks within the main
window: boundary `abs(d)<=12`, foreground interior `d>=32`, background interior
`d<=-32`, and the remaining transition pixels. Save all mask hashes and counts.
The edge mask measures an explicitly simulated boundary; it is not the project's
real occlusion-halo population or its M8 census.

## Geometry and sampling phase must be explicit

Read only the already-published derived file
`experiments/M103-halfdrift/data/truth-dense.json`, recording its exact hash.
Choose rungs **[0,32,64,96,144,184,224,264,298]**. For output frame k set
`s_k=exp(ladder[rung_k].ln-ladder[144].ln)` and explicitly serialize `s_4=1`.
Preserve all nine values; fit no polynomial. Re-evaluate corner displacement
and chord departure on the small benchmark in its own native/quad units. Do
not repeat “46.1 px” as this small fixture's displacement. Assert nonzero
interior curvature and include a chord-replacement control with identical
endpoints. The latter must produce different consumed per-frame coordinates;
its reconstruction effect is a measured outcome, not assumed to have one sign.

M25's forward warp is `z=c+s_k*(q-c)` from canonical scene q to frame z;
production gather pulls from z, so use this **forward map as the production
placement**, in quad units, without another inversion. The production reference
is frame4, not an implicit frame0. No alignment solver is under test. The latent
and ideal scene are deliberately defined in frame4's identity gauge even though
M25's `ground_truth` docstring calls its unwarped gauge “frame0”.

The phase convention cannot be guessed from S. For latent array index i on
either axis define native coordinate
`q=(i+0.5)/S - margin - 0.5`. Sensor cell x therefore covers `[x-.5,x+.5]`,
with midpoint subcells. M25's warp centre is expressed in array-index units;
set its `Breathing.centre_x_px` to
`183-320/2+0.5-0.5/S` and its y equivalent to
`101-240/2+0.5-0.5/S`. Recompute these offsets for the S=8 convergence control.
Otherwise a supersampling sweep silently moves the physical scale centre.

For production's centre `c_p=(80,60)`, off-axis physical centre in quad units
`c_q=(91.5,50.5)`, set complex similarity `a=s_k`, imaginary part0,
`b=(1-s_k)*(c_q-c_p)`. Then `apply_at(u,c_p)=c_q+s_k*(u-c_q)` and each native
CFA site is pulled at its own offset. Check all four parities and off-axis
landmarks against independent coordinate algebra. Save the output map
`canonical_native = output_native + 2*crop_origin` from the actual domain.
No output image registration, brightness fit or output-driven crop is allowed.

## References: three names, three different questions

**Ideal latent reference `T_ideal`:** geometric front-to-back scene composite,
integrated over the canonical sensor cell, with no diffraction, defocus or
noise, expressed after the same *known* fixed WB/gain normalization as the
output. For scene3 this is a hypothetical sharp visibility boundary. Report
RMSE/bias against it as *ideal-scene discrepancy under the specified model*;
the deficit includes unavailable optical information. Never call it attainable
or interpret distance from it as the merge's removable loss.

**In-focus observation reference `T_obs` for scene2:** independent analytic
cell-integrated scene after the specified in-focus diffraction transfer at
frame4, which is identity geometry and exists in the bracket. For a wave with
frequency vector f, multiply its amplitude by the independently evaluated
diffraction response at `abs(f)` and by
`sinc(fx)*sinc(fy)` for the unit-square pixel aperture. For the discrete S-point
quadrature commission use its exact finite-sum aperture factor instead; do not
pretend finite quadrature is the continuous aperture. This reference describes
the specified noise-free optical observation, not the unblurred object. It is
recoverable in the analytic band-limited scene model; the finite production
demosaic need not reproduce it exactly.

**Attainable algorithm comparator `Y_single`:** run the actual production path
with just the known best-focus input, holding its original known placement,
full-plane centre, frozen nine-frame crop and writer settings fixed. For scene2
this is frame4. For scene3 use frame2 on the frozen foreground-interior mask and
frame6 on the background-interior mask, and report the two actual single-frame
outputs separately at the boundary. These are realizable outputs using available
observations. They are **comparators, not mathematical lower bounds**; averaging
can reduce their noise and a selector can lose to a merge at an occlusion edge.
Do not assemble their boundary pixels into an “achievable oracle” and assume it
can attain `T_ideal`. Retain both noisy and noise-free versions when interpreting
the source of a difference.

M25's returned `sensor_radiance` is an unblurred geometric truth convenience,
and its `best_frame` is nearest to a geometrically averaged focus map. Neither
is a ready-made attainable full-image reference. Build the scored references
independently and preserve these distinctions in field names, tables and plots.

## Normalization and reported quantities

Decode actual RGB16 TIFFs, preserve their file/pixel hashes and declared camera-
linear metadata, and use the fixed conversion
`Y_DN = TIFF_u16 * (15360-512)/65535`. Do not subtract512 again from a developed
TIFF. Its black subtraction already occurred. Scene2's desired achromatic
target in these units is `0.25 * radiance_e`; scene4 is already in these units.
Use the explicitly frozen WB coefficients actually consumed (including their
f32 representation); verify constant-color patches so rounding is not mistaken
for a spatial defect. No gain, offset, histogram or contrast fit to an output.

Report per channel and per fixed region: RMSE, signed bias, and repeat temporal
variance. Keep RGB error and green error separate; do not pool a variable
mean/color normalization into a single score. In scene2 also report recovered
amplitude and phase of the two independently specified waves, from the same
fixed mask and reference convention. This discloses attenuation hidden by a
noise-reducing blur. It is not a general learned/perceptual detail metric.

Start with **8 independent noisy repeats**, seeds `[701,709,719,727,733,739,743,751]`,
and one noise-off version of each scalar scene. The first analytic color fixture
is noise-off; its first purpose is to isolate channel, phase and gather errors.
Cache expected electron frames
once, then draw each repeat from them; do not re-render FFT optics eight times.
Use sample variance (`ddof=1`) across repeats at each pixel, then pool within the
fixed mask. Do not call spatial SD over texture temporal noise. Report the mean
squared error decomposition against each named deterministic target: squared
error of the repeat mean plus `(7/8)*mean(sample_variance)`. For bias-squared
estimation, also expose the finite-repeat correction `mean(sample_variance)/8`
and its possible negative result; do not clip it into a flattering statistic.
Eight repeats give a development diagnostic with explicit uncertainty, not a
precision noise certificate. A matched seed identifies paired input draws;
different output modes must consume the same input bytes.

No single production RMSE is required to worsen under blur: smoothing noise can
improve MSE. The metric's failure direction is loss of high-frequency detail on
low-contrast/noisy scenes, potentially hidden by reduced variance. The specified
wave response and noise-off target controls expose that tradeoff. Known-target
blur, known added noise and known color bias below have unambiguous signs.

## Required forward-model controls, before product comparisons

These are proposed commissioning predicates, not observed passes. Every
negative has an unchanged/placebo arm and every numerical tolerance must be
frozen before running. If a numerical budget fails, stop that result or run the
predeclared refinement; do not increase the tolerance based on a candidate win.

For the small isolated operator controls, propose absolute complex transfer
error <=0.002 after independent quadrature convergence, DC error <=1e-8 DN,
and exact finite aperture/hand alpha arithmetic within1e-12 in f64. The
textured alpha/direct-convolution control uses <=0.5 DN RMS reference agreement
and must exhibit >=2 DN RMS separation from the wrong-order arm. Noise null
covariances use absolute correlation <=0.02; the correlated negative is planted
at correlation0.25 and must exceed0.15. Identical-frame noise must have
correlation>=0.99 and fail temporal independence. These are deliberately finite
engineering controls, not a parameter sweep. If the proposed stimulus cannot
clear its own separation, its dependent conclusion is unmeasured.

| Property | Independent control and a realizable rejecting input |
|---|---|
| Flat/DC and no shared-axis filtering | Constant opaque layer must remain constant before exposure under every focus/scale. Isolated layer/channel/frame changes must not smear another axis. Nonconstant sinusoid proves the blur path executes. |
| Defocus blur | In an isolated periodic scalar plane, compare the produced Fourier coefficient to independent real-space integration over a uniform circular disc, using fixed quadrature and known sinusoidal input. Test CoC0 and CoC4 at axial and diagonal frequencies; preserve the negative-lobe sign on a suitable separate high-frequency component. Radius/diameter substitution or clipping the OTF's negative lobes must reject. This checks the declared disc model, not real bokeh. |
| Diffraction | Directly inspect transfer on a periodic sinusoid/impulse, against independently computed pupil-overlap area (two unit discs separated by twice the normalized frequency, numerical area integration). Compare zero, an interior normalized frequency and above-cutoff frequency. Deleting diffraction, changing wavelength or doubling N_eff must fail this check even when a noise-selection score stays unchanged. Do not use `OtfCache.total` to supply its own expected term. |
| Alpha and order | First use a tiny **discrete** hand-check: background B=10, foreground F=30, alpha `[...,0,0,1,1,...]`, foreground kernel `[1/4,1/2,1/4]`, sharp background, periodic boundary. At the two transition cells the correct `blur(alpha*F)+(1-blur(alpha))*B` is15 and25. Omitting blurred alpha or multiplying separately blurred radiance by alpha must disagree. This scalar arithmetic control is insufficient alone: repeat a textured two-depth plane with different blur kernels against an independent direct spatial convolution and the registered boundary mask; composite-first must differ beyond its independent quadrature error bound. |
| Pixel aperture and CFA | For an affine ramp, each pixel's box mean equals its centre value. For a known wave, compare the exact finite midpoint sum and continuous sinc factor. Explicitly mutate integrate-before-mosaic to point sampling and then to integration at quad pitch; the appropriate amplitude/phase/parity checks must reject. Use different R/G1/G2/B diagnostic addresses, nonzero active origin and spatial chroma, so a shape-only pass cannot hide a half-pixel or channel error. |
| Supersampling and circular-wrap error | Re-render **one noise-off** instance at S8 with the same physical coordinate convention, and with margin96 instead of48. Compare expected pre-quantization signals on every frozen ROI. Initial engineering budgets: <=1 DN RMS in the plane/interior masks and <=2 DN RMS in the boundary mask after known WB/gain normalization; also report maxima. If S4 fails, keep its failure and use S8 only after S8 vs S16 clears the same budget. If margin48 fails, keep it and validate96 vs192. These are numerical approximation budgets, not camera accuracy; an effect smaller than twice the observed numerical difference cannot rank candidates. |
| Expected-frame observation | If the producer intercepts M25's final `expose` call to cache pre-noise electron arrays, run original versus observing delegate versus allocated-but-disabled placebo with the same seed. Actual u16 frame hashes must be identical. The wrapper must forward unmodified arrays and restore its module state; use an isolated module/process so this does not change another run. |
| Quantization and clipping | Constant values on either side of rounding ties, black/white boundaries and above white must reproduce independently specified rounding/clipping. Keep the benchmark's normal input/output rail counts zero; a separate saturated control must produce a nonzero counted rail population. Quantization error is not an optical defect. |
| Noise | On separate 128x96 flat arrays at electron means0,4096,16384, use64 cheap exposure repeats without FFTs. Verify per-pixel temporal variance in raw DN, pooled per parity, against `g^2*(E+RN^2)` with an explicit discrete rounding correction (rounded-normal bin probabilities for the dark arm). One-percent variance tolerance at the bright levels and two-percent at the dark level are proposed. A factor-two gain/model mismatch, removing read noise alone, frame-identical noise and correlated noise with matched variance must be detected by variance and off-diagonal temporal/spatial covariance checks. Their unchanged controls must pass. Independent affine-law calculations validate the synthetic operation, not physical g/RN calibration. |
| Error scorer | On the exact noise-free analytic target, inject +20 DN constant error, a known phase shift, a channel swap and 0.6-native-pixel Gaussian blur; absolute bias, color/phase and wave-amplitude errors must respond. Flat no-op and empty mutation remain zero. Added independent zero-mean noise increases expected target MSE; average16 independent copies gives a known variance reduction on the flat. Do not nominate bilinear as an unconditional defect. |
| Geometry consumer | Chord substitution changes interior maps without endpoint change; wrong pull inverse, incorrect scale centre, omitted CFA offsets, wrong crop origin and same-size false output translation must fail independent coordinate/image checks. Retain the fixture's trusted parameter/mask binding before outputs; a rehashed descriptor cannot certify the wrong map. This test-local known-map check can use M194 immediately. A general real-output M193 adapter, discussed in `review-output-adapter/audit.md`, is separate work and is not a prerequisite for scoring this synthetic grid. |

For the alpha test, a single constant-layer blur happens to commute with some
alternative orders. That is why the textured, different-PSF control is required
as well as the hand-computed four-value transition. In no case may the control
be normalized with a free constant fitted from the same output it tests.

The primary noisy runs can be drawn from cached expected mosaic electrons,
using M25 `sensor.expose` only after its independent controls pass. Prefer a
small observer around `render_stack`'s existing final exposure call to duplicating
its optical/compositing loop. The only generic RGB branch is the separate
analytic component fixture; adding RGB support to M25's warp alone would leave
blur, alpha broadcasting and ground-truth composition uncommissioned.

## Smallest implementation after allocation

Proposed new, kebab-case files (names are not a milestone claim):

1. `experiments/production-known-scene/preregistration.json`: exact scene,
   coefficient, seed, geometry, reference, mask, numerical-budget and software
   bundle freeze; all successful/refused/failed outcomes explicit.
2. `produce.py`: imports frozen M25 `config.Sensor/Optics/Capture/Breathing`,
   `scene.Layer/Scene`, `render.RenderConfig/render_stack`, and
   `sensor.expose/pixel_aperture_integrate/mosaic`. Constructs only scalar M25
   radiance, observes expected electrons, and writes u16 little-endian CFA
   frames plus a strict JSON manifest. Store expected RGB/alpha truth only for
   this bounded fixture; stream per-frame products and release latent buffers.
3. `commission-forward.py`: independent pupil/disc integration, direct discrete
   alpha convolution, analytic aperture/parity/noise/scorer controls. Do not
   call the producer's OTF to calculate expected results. It should exit nonzero
   on a failed scene/model control rather than merely print a warning.
4. `crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs`: an opt-in ignored
   test child module beside M194, with a minimal `PyramidFrameSource` over the
   hashed fixture files and strict frame sizes/levels. Construct
   `PreparedPyramid`, exact `WarpMap`, actual Crop domain and explicit synthetic
   `NoiseModel`; call **`run_pyramid_prepared`**, sharing the production
   `load_frame`, gather/gate floor, canonical fold, confidence rereads and
   `write_merged`. Add only its cfg(test) module declaration to `merge_cmd.rs`.
   M194's test-only `run_fixture` currently chooses `profile::noise_model_for`
   and uses path-stimulus metadata, so it is not the known-noise benchmark
   adapter unchanged. Reuse its seam pattern without copying the merge body.
5. `run.py` and `score.py`: sequential execution with at most two CPU threads;
   verify actual TIFF dimensions/metadata/hash, fixed input-to-output mapping,
   predetermined references/ROIs, repeat errors/variance and full refusal
   accounting. Save commands, resolved environment and all controls. Do not
   invoke example mains that include real-capture stages.
6. Independently owned `independent-verify.py`: re-choose scene aspect ratio,
   foreground orientation, color phase, curvature interior perturbation and
   noise seed. Verify the actual consumed frames and TIFFs; byte-identical
   observing/no-op wrappers and live output mutations are mandatory.

The entry point can remain an explicitly invoked ignored Rust test while this
is developer commissioning; there is no reason to ship a new user CLI flag or
broaden the public API yet. Use a unique target, visible compile evidence and
one test thread. M194 must first finish its source and independent byte-lineage
closure; freeze that accepted revision before consuming it here.

First stop point: the finite flat/plane/color controls and one pinned production
baseline on those three fixtures, with the named references and eight noise
repeats for flat/plane. The two-layer extension is a small separate step; its boundary results
remain model diagnostics unless its own controls pass, and never imply real
occlusion-halo qualification. Publish supported discrepancy/noise numbers and
every failed control. Only then preregister **one** admission change on the same
development fixtures. A negative or unrankable result is useful; physical
validation remains separately unmeasured rather than silently inferred.

## Remaining model and API dependencies

There is no identified need for a public API or general RGB-renderer change to
execute the first three fixtures. The remaining dependencies are concrete:

- **M194 revision closure:** freeze the accepted seam and byte-lineage result
  before building this child module. Its existing helper cannot be used
  unchanged: it performs profile noise lookup, identifies reference0 and accepts
  a caller-supplied crop. The new private adapter must inject the declared noise,
  use reference4, and obtain its frozen domain from actual cover preflight.
- **Expected-electron access:** M25 exposes final u16 frames, not the expected
  mosaic electrons needed to avoid repeated optical work. An isolated local
  wrapper of the existing final `expose` call is sufficient; it must forward
  unchanged inputs, restore the imported function, and pass byte-identical
  on/off/placebo controls before its cached arrays are consumed. No M25 source
  edit is needed.
- **Numerical optics and phase:** the proposed transfer and convergence budgets
  are unrun. A failure blocks the affected optical-reference claim, with the
  failed fixture retained. Flat and independently analytic color checks remain
  executable. The two-layer alpha/order check is a later dependency of that
  fixture, not a prerequisite for these first three outputs.
- **Producer-to-consumer contract:** serialize active dimensions/origin, CFA
  phase, scale values, fixed WB, black/white levels, explicit noise coefficients,
  quantization, actual crop and CameraLinear writer settings. Independent
  coordinate and constant-patch checks must reject a wrong convention before
  scoring; a successfully decoded TIFF alone does not establish that contract.

Physical camera calibration, spatially varying chromatic defocus, real
occlusion-halo fidelity and a universal attainable reference remain outside
the admitted scope. They are not unresolved implementation choices for this
first benchmark.

## Audit commands executed

```powershell
python experiments/ORCH-drift-check/prior_art.py forward model truth benchmark
rg -n 'FAIL|Gate|occlusion|diffraction|integration' docs/research/M25-simulator-measured.md
rg -n 'scene|truth|oracle|SCENE NOT COMMISSIONED' docs/research/BUILD-BLEND.md
rg -n 'SCENE NOT COMMISSIONED|fn run_scene|Ok\(\)' crates/strehl-cli/examples/blend-truth.rs
rg -n 'analytic|control|truth' docs/research/BUILD-DEMOSAIC.md
rg -n '46.1|curvature|per-frame|gauge' docs/research/M103-halfdrift.md
rg -n 'trait PyramidFrameSource|struct PreparedPyramid|fn run_pyramid_prepared' crates/strehl-cli/src/merge_cmd.rs
rg --files experiments/m25-simulator/src/strehl_sim
```

Targeted source/report reads followed those searches, including M194's current
`production-truth.rs`, the M25 optical/sensor/render APIs, the independent
producer-scope artifacts, and the current `2026-09-sota-program.md`.
No producer, optical control, benchmark, build or product run was executed in
this planning task. The proposed tolerances and expected outcomes above are
not measurements.
