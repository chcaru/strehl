# Independent direct-radiance controls

Frozen before execution. Root runs four tests of the actual new Front/Stream
operator, then may execute the separately authorized one complete chip pair.
These small tests consume f32 plane arrays at the accumulator boundary; they
do not qualify RAW decoding, camera calibration, rounded CA/MHC sampling or
final photographic quality. The full adapter must separately prove its actual
gather/current-baseline identities. No generic new rendering framework is added.

1. `address_gauge_and_destroyers`: nonzero x/y slopes, unequal normalizations,
   hand-calculated native quad centers and a nonuniform schedule. Omitting the
   factor two or adding the crop again must fail. Source/channel codes check
   common weights across four planes. There is no local source argmax.
   Instrument repair after controls-1: the first original point cancels the
   wrong-factor error exactly, so the original single-point destroyer failed.
   Both original positive points are now used and detection is required at
   least once (>0.01), not at every point. Their wrong-factor values/errors and
   the first point's degeneracy are retained. No point, operator, image fixture
   or quality bar was changed.
2. `constants_source_and_uniform_mean`: 299-source high-DN and negative constant
   planes under varying weights use a standard conservative f32 summation and
   division bound, not an invented photographic tolerance. A one-supported-
   source limit must return the supplied signed radiance exactly. A separate
   deliberately uniform-weight fixture must equal its known arithmetic mean.
3. `planar_focus_and_flat_noise`: flat independent noise runs first. The narrow
   average must reduce its MSE by at least 25% relative to the average single-
   source error; its higher noise than the all-source mean is explicitly live
   and recorded. A fixed 33-source nonuniform schedule and known spatial plane
   modulate locally blurred coloured sinusoids. Truth is the corresponding
   focused signal. Candidate radiance MSE must improve at least 25% over the
   all-source mean. Shifting the front by +0.35 while holding the sources and
   schedule must fail that same bar; erased detail must fail too. This analytic
   spatially varying attenuation is a local-blur approximation, not an occlusion
   simulator or a calibrated physical PSF. All four channels use the same front.
4. `refusal_and_order`: wrong/duplicate/incomplete order, invalid plane count,
   nonfinite samples/model, finite-input sum overflow, and zero total mass must refuse. A zero-mass image
   cannot become an apparently successful baseline placeholder.

The random draw is independent across source/channel/pixel with fixed seed and
20-DN standard deviation. It commissions averaging, not the injected sensor
noise model. No noise constant fitted to the test is used to claim calibration.
Radiance MSE can reward smoothing a noisy truth, so the structured comparison
uses noiseless focused truth plus a separately executed flat control and an
erased-detail destroyer. Neither this positive nor numerical correctness implies
occlusion safety or actual chip benefit. No thresholds, widths, sources or
fixtures change after measurement; a negative remains a negative.

Four JSON receipts (`address`, `identities`, `planar`, `refusal`) and the exact
four test names are retained by the runner. All mechanical flags and the planar
positive/destroyer/flat flags are required before the observational RAW run;
`actual_native_quality_qualified` stays false. The root's separately approved
scope does not convert the failed two-band focus-front proxy into a pass.

This is distinct from earlier coarse/full-AC reweighting because it changes the
complete radiance, including DC. The prior native-coherent-estimator already
used full-radiance coherent averaging; this is not a new reconstruction class.
The distinction is the globally fitted plane/nonuniform schedule rather than
the earlier legacy Tenengrad election and gate. The fitted width remains an
unvalidated reconstruction bandwidth, with no tuning. Whole-field extrapolation,
texture-dependent focus response and local depth variation remain risks.
