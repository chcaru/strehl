# Independent angular-spectrum controls and decision

PREREGISTERED 2026-09-09 before root's numerical execution. Source/API review only so far. The charter, alignment-direction.md and next-decision.md bind this closed population. The independent controls do not decode RAW, read hidden radiance or invoke the estimator at import time. Root owns the bounded execution and all commits.

## Frozen identifiability choices

Use the design agent's single 512x512 analytic Gaussian-mixture field and declared three arms, plus the same seven-rung full-image radial null and exact separable-spectrum null. The image is evaluated directly at transformed coordinates with exact Gaussian convolution; this is not a calibrated circular-pupil defocus or opaque-visibility simulation. The operator receives images/descriptors, never rung labels, planted scales or blur parameters. Angular structure changing with radius is required; large angular contrast alone is insufficient.

Sampling is fixed at 512 log-uniform radii 4..64 FFT bins and 256 full-circle angles, relative magnitude floor 1e-8, Cartesian logarithm before bilinear polar sampling, du=log(16)/511 and maximum integer lag floor(.14/du). Correlate the same central radial support at every lag, without wrapping or lag-dependent cropping. Ordinary and centred descriptors use identical Fourier samples. No image-space NCC stage may overwrite the reported direct scale.

Before either descriptor can supply a scale, its globally mean-removed RMS must be at least 0.01 in log-magnitude units. This fixed engineering contrast floor prevents normalizing tiny interpolation/FFT anisotropy into apparently strong information. It is not a noise-derived confidence interval. Then compute the central derivative in log radius, remove its global mean and its projection onto the mean-removed descriptor (NCC's gain nuisance). Require residual derivative energy divided by descriptor energy >=1e-3 on both inputs. The information test uses the same fixed central support as the match.

This extra projection is necessary: Q=A(theta) loses scale entirely, while Q=exp(2u)A(theta) has nonzero radial derivative but a shift changes only overall gain. Normalized matching cannot distinguish that gain-only shift. Both are mandatory nulls. An informative match additionally requires an interior best integer peak and a margin >=1e-3 over every other distinct local maximum and both search endpoints. Ties/periodic aliases refuse. Only then may a finite three-point parabolic interpolation within half a bin refine the peak. Sharpness is never a substitute for the information and energy tests.

The independently authored literal controls recover signed shifts -3,0,+4 bins on a radius-dependent angular field, with log-scale tolerance 2e-4. They verify cancellation of an independently added radial nuisance while ordinary retains it; structured separable refusal; gain-only refusal despite nonzero derivative; exact radial/weak/nonfinite refusal; and periodic-peak ambiguity despite positive derivative information. These are cheap operator controls, not additional scored image populations. A failed control is retained and stops the run; no output-guided threshold or fixture change is authorized.

## Curved gauge and finite decision

Use exactly M103 rungs 0,8,64,128,144,200,298, with stored absolute ln values independently checked against the saved seven scale literals. The expected log scale is ln_j-ln_144. Signed placement error is (estimated_ln_scale-expected_ln_scale)*R, R=0.5*hypot(3516,2344). These are original M103 scale-equivalent CFA-plane corner pixels, not pixels in the 512x512 analytic image. No rotation, translation, connected-graph solve or native placement accuracy is inferred. Report every rung, including the self-pair and curved interiors, with every refusal visible.

The maximum admissible centred error is 2.0 scale-equivalent plane pixels on **every** rung in no blur, unequal radial blur and the fixed two-depth/window violation. The zero-error truth-versus-itself identity is arithmetic, not independent evidence. Its sign reversal and straight log-scale chord re-gauged at 144 must fail this tolerance; rung 200 must independently expose the curved-interior chord error. Endpoints alone cannot pass this consumer test.

For a finite quantitative advantage in unequal blur, both ordinary and centred arms must admit all seven rungs. Centred mean absolute error must be <=0.8 times ordinary mean error, and centred maximum error must be no worse. Require the same advantage and per-rung cap in the fixed two-depth/window violation. The 20% mean reduction is fixed before execution so arbitrarily small numerical differences cannot become a headline mechanism gain. No-blur establishes baseline direct-scale correctness, not an advantage requirement.

If ordinary refuses, report any centred availability gain separately; missing errors are not infinity and an accepted-subset mean cannot establish full-track superiority. Such an arm does not pass the quantitative advantage criterion. A centred refusal, error-cap failure, failed null, no informative-premise advantage, or lost advantage under the fixed violation stops this direction. Do not sweep the window, frequency support, blur width, confidence thresholds or analytic field. Any synthetic pass would only support a subsequent source-level decision; it cannot admit native alignment or SOTA quality.

The exact separable arithmetic null and full-image radial null must refuse centred estimates at all seven rungs, including self. Ordinary may retain radial information; its null outcomes are reported rather than forced to match the centred null. The extra gain-only descriptor null separately tests the normalized estimator's identifiability. No near-null confidence from raster artifacts is tolerated by changing the frozen floor afterwards.

## Source compatibility and limits

The reviewed operator keeps float32 image/descriptor/derivative arrays, complex64 scipy FFT output and explicit float64 measurement reductions. It uses a fixed reference support at every searched lag and returns direct scale=exp(-refined_lag*du), with scale/log_scale absent on refusal. The driver uses image(x)=field(x/scale) and the same stored relative scale, so the independent signed-shift control tests the sign convention on a separate descriptor input. All five image/arithmetic arms and both descriptors remain in the result, including conditional accepted-only summaries explicitly labelled as such.

No numerical experiment or control was executed by this reviewer. Held independent-controls.py is 6263 bytes, SHA-256 ff39fd13a34eca16c369853fea9bea86f140ac47f39eaf84b4a4f7d79c634d70. The fixed full-image experiment, its budget, nulls and per-rung results remain to be executed by root. The Gaussian radial-blur premise and additive-layer/window violation do not exhaust real defocus, nonradial apertures, occlusion, sensor noise, OTF zeros or finite native-image support.

## Executed independent decision, 2026-09-09

**REJECT / close this fixed direction without tuning or native execution.** This section records the completed root execution; the preregistration above remains unchanged. The machine-readable decision is decision.json. The prior review was 6997 bytes, SHA-256 b556bff42db800ddcae59013ff73970df115b268e1bd3f6937d86659e753c88b, and remains pinned as that pre-execution artifact in the decision.

VERIFIED from stored receipts: root executed source c2cfd3bb6325acaf1fb800a94f96d77a058b0818 once with `Python312/python.exe -I -B experiments/alignment-angular-spectrum/experiment.py --output-dir experiments/alignment-angular-spectrum/run-1`, through execution-1's bounded runner. All 70 unique arm/descriptor/rung records are present: five arms, two descriptors and seven rungs. Invocation source hashes matched the held files at review time. The process exited 0, recorded no error or cleanup error, and closed its job without forced cleanup. Recorded wall time was 1.750 s, owned CPU 1.109375 s and peak job commit 52,633,600 bytes (50.1953 MiB). These are this tiny experiment's costs, not a native speed benchmark. The reviewer read source and saved artifacts and derived the comparisons below; no experiment, estimator or metric was rerun.

Bindings: run-1/results.json is 73792 bytes, SHA-256 491d1f984625dd64641179c34eef9a0f691392e0cb819a863630136add3ff8ff; run-1/controls.json is 8021 bytes, SHA-256 9fa9f1c0ed8914197e6cf058db795cd7c1ec3bdb59de014472c308989062789d; execution-1/process.json is 2760 bytes, SHA-256 1c4ca1261c14bbfb831d2ecb25d0233192eca74797c52967c673a9e4f2271e81. Held operator.py SHA-256 is 1c5106684dbeda1997f75837a71b44a5dd671e855668f1d775e3e4ccbbd5fae4, and experiment.py is 9b6a765cba6095f7ce89c029d71a3201d85ce7834670cec17b3c70fb815eb918.

MEASURED operator controls pass. The signed literal shifts and radial-nuisance cancellation recover within the frozen log tolerance. The nonconstant separable descriptor and nonzero-derivative gain-only descriptor refuse for insufficient scale information. The periodic descriptor has positive information but zero peak margin and refuses as ambiguous. The exact radial descriptor illustrates why the separately chosen absolute energy floor matters: its residual mean energy is approximately 1.52e-15 while normalized derivative information is about 3590.94; it correctly refuses as weak energy. The weak-contrast control similarly refuses despite positive information. These controls reject sign, information-loss, weak-energy and alias errors on their actual paths; they do not validate confidence under a changed image model. The sign and chord gauge destroyers exceed the cap, and the curved interior at rung 200 gives 4.07481 plane pixels of chord error. Truth against itself remains labelled arithmetic.

Every error below is in the preregistered reference-144 **M103 scale-equivalent CFA-plane corner-pixel gauge**, with radius 2112.85304742 plane pixels. It is not displacement measured in the 512x512 test image, an end-to-end frame-0 result, or native placement accuracy.

| Fixed arm | Ordinary accepted | Centred accepted | Ordinary mean / maximum absolute error | Centred mean / maximum absolute error |
| --- | ---: | ---: | ---: | ---: |
| No blur | 0/7 | 6/7 | unavailable | 0.021041 / 0.041972, conditional |
| Unequal radial blur | 0/7 | 6/7 | unavailable | 0.021410 / 0.040924, conditional |
| Two-depth/window violation | 7/7 | 7/7 | 8.260266 / 21.924637 | 13.042398 / 38.727694 |

The premise result is useful but incomplete: both centred premise arms refuse rung 298 as ambiguous, with peak margin approximately 0.000202 below the fixed 0.001 threshold. Ordinary refuses all seven as ambiguous. The small centred errors describe accepted subsets and an availability gain under this field, not a complete-track numerical advantage. Treating ordinary's absent errors as infinity or dropping the refused endpoint would change the frozen decision. No threshold relaxation is justified by this result.

The fixed violation supplies the decisive complete comparison. Centred mean absolute error is 1.57893 times ordinary and its maximum is 1.76640 times ordinary. All six non-reference centred estimates pass the frozen confidence conditions yet exceed the 2.0-pixel error cap. Thus the failure is not merely a refused endpoint or an average dominated by one frame.

| Rung | Ordinary signed error | Centred signed error |
| --- | ---: | ---: |
| 0 | -11.409680 | +2.679634 |
| 8 | -10.481273 | +3.702701 |
| 64 | -5.602397 | +8.934681 |
| 128 | -0.817928 | +13.929472 |
| 144 | -0.052011 | -0.046265 |
| 200 | +7.533938 | +23.276341 |
| 298 | +21.924637 | +38.727694 |

DERIVED independent re-choice: excluding both endpoints and retaining the self-reference, ordinary mean/max absolute errors are 4.897509/10.481273 and centred are 9.977892/23.276341. Excluding the self-reference as well leaves rungs 8,64,128,200: ordinary 6.108884/10.481273 versus centred 12.460799/23.276341. The rejection survives both choices. In particular, the curved interior rungs 128 and 200 become substantially worse, even though the earliest rungs 0 and 8 individually improve. Those isolated improvements cannot establish the consumer's per-frame guarantee.

MEASURED fixed nulls: all seven centred radial-image cases refuse as weak energy and all seven centred separable-spectrum cases refuse for insufficient scale information. Both ordinary null populations also refuse (their reasons remain in the saved records), for 28 refusals across both descriptors. This establishes the required finite null behavior, not a universal calibrated confidence guarantee.

ARGUED physical conclusion, bounded by these inputs: removing the radial angular mean can preserve useful scale structure while cancelling a single radial log-spectrum nuisance. Under the fixed additive two-depth/window violation, the nuisance is no longer removed in a way that preserves accurate direct scale, and this confidence policy admits materially wrong estimates. The source is rejected as a deployable alignment direction under the frozen protocol. This does not prove that every angular-spectrum method is impossible, that real pupil defocus is Gaussian, or that all native scenes behave like this analytic field. No native decode, image alignment, RAW calibration, full geometric solve, or SOTA quality claim follows. The finite experiment is closed; no output-guided support, threshold, field or blur tuning was performed.
