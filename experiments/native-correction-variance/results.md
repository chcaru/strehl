# Local correction variance approximation: rejected

2026-09-09. **MEASURED.** One fixed synthetic original-CFA ensemble rejects the proposed sparse variance addition at the registered consumer. No production variance behavior or default changes. The earlier local photographic improvement remains experimental; this result does not retract its visible result or establish its noise fidelity.

Source commit e2b15119a0378941d4cfb98d23bf2ec59813b9f2. Root executed:
- python -I -B experiments/native-pyramid-profile/build.py --direct-planes --correction-variance --output-dir experiments/native-correction-variance/build-2
- python -I -B experiments/native-correction-variance/run.py

Build2 freshly compiled strehl-cli and completed in94.031s. Held test executable SHA256883eb304c8247a68025c800d0f99b3ea74a5d73a65f53faeed4a9c04db6708bc. Earlier source17117f31 independently passed the two-route smoke; both smoke and full run ended normally with terminal Job accounting and no intervention. The fixed numerical allocation used3.21875 aggregate childCPU seconds including smoke; full ensemble2.109wall seconds,8,454,144B peakJobcommit. These are diagnostic costs, not production speed results.

## Decision and scope

Exactly8cells x64paired noisy originals generated32rows: flat/textured, identity/held nonidentity warp, shot/read, two Laplacian bands and core/adjacent masks. Actual u16 correction, Malvar/gather, G1/G2 luma, original Probe beta and production pyramid/smooth5 kernels ran. No originals were decoded, no new photograph rendered, no gain/noise/geometry/seed sweep. The translated discrete maximum gain was1.0583255291.

All independent arithmetic/decision controls passed. All16core increments were positive and sufficiently resolved. All4required wrong shot/read-factor checks rejected their nominated destroyer. Therefore the result is **REJECT**, not insufficient power.

All8core band1 rows failed the fixed local-delta tolerance. The proposed added-noise prediction overstates the measured *increment* by10.7207% to27.7198%; the corresponding discrepancy is0.77% to1.92% of corrected total band variance. Neither quantity is a visible-image severity score. All8core band0 rows and16adjacent rows pass their prescribed tolerances. Adjacent increments are very small and their absolute baseline-floor allowance dominates, so these passes do not prove precise boundary propagation.

The comparison subtracts corrected/off temporal variances after actual smooth5, with paired delete-one uncertainty. It includes the current predictor's shot increase from the brighter corrected signal as well as the proposed missing term; it is neither Var(corrected-off) nor just the added buffer. Baseline model bias is reported separately and not fitted away. A wrong calibration cannot be tested when the generator and predictor share it. The current spatially pooled beta, gain variation across filter support and source covariance remain plausible contributors, without unique attribution.

Unity controls establish numeric equality for consumed planes, luma, beta, variance and bands and retain off-arm hashes. They do not retain paired intermediate byte hashes; signed-zero equivalence is therefore a receipt limit. No complete output-byte claim is made. The nonexistent-path fixture resolves CA=None and supplies no positive nonidentity-CA coverage. The Gaussian shot approximation and quantized standardized draw do not establish photon statistics or calibration.

## Program action

Close this local approximation without a band-specific adjustment, fitted beta, new covariance engine, wider gain or another render. Retain its test-only seam and evidence for future work, and keep the manually nominated correction experimental.

The broader program moves to the still-open final NCC peak interpolation: a finite windowed-sinc candidate for subpixel placement, judged first through actual generated-field correlation calls, then (only if admitted) per-frame real-stack placement in the merge's reference gauge. See ../alignment-sinc-peak/charter.md. No SOTA claim follows from this test.

Bound primary measurement: run-1/measurement.json,134414B,SHA256b466ff301a9305c1b746494449d582e7f9f5a2d97ba06ea8d789334758b65575. Independent source/result interpretation is owned separately in independent-review.md and independent-results.md.
