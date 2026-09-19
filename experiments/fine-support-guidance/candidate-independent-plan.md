# Independent fixed finest-band candidate screen

Frozen design before any candidate numerical result. Root builds and executes;
the implementation author does not validate this screen. This tests only the
extra radius-32-quad pooling of the existing finest-band energy and injected
floor. Every higher band and the base must retain bit-identical accumulations.
There is no cross-band propagation, new fallback, radius sweep or calibration.

Reuse the earlier generated actual-u16-consumer arrangement: five 320x288
native CFA frames, active origin (7,11), padded stride, non-unity camera WB,
the same five independently planted fractional similarity maps, asymmetric
quad crop (7,9,145,125), actual source gather/noise probe/BandMerge, and final
camera-linear MHC RGB. Inject the existing ISO100 and ISO400 sensor model
separately. This shares the model with the consumer and therefore tests the
operator, not external accuracy of that noise calibration. Source arrays must
remain unchanged. Check Mode::Off exactly against the actual baseline at both
ISOs and require actual candidate output changes in the structured case.

A compact hook control independently sums the literal 65x65 energy/floor
windows at six interior/edge points on a 129x97 unequal field, then checks
the actual weight hook at exponent1 against its documented excess/floor/64
formula. Both zero and positive admission must occur. Zero energy at exponent8
must remain zero. This is an operator check, not another image-quality score.

Three fixed scenes, each noise level evaluated separately, flat first:

1. Uniform camera-linear RGB 0.25 with independent source-sensor noise.
2. A compact coloured glint at native (122,120), focused at frame0, whose
   other four observations use centered anisotropic Gaussian PSFs with
   conserved continuous flux, increasing length and slightly differing colour
   angles. This is a falsifiable adversarial PSF, not a calibration of the
   Sony/Viltrox optical train. A nearer coloured textured surface occupies
   x>=176 and focuses at frame4. Render it with the M13 two-layer rule:
   blurred premultiplied near texture plus (one minus blurred near coverage)
   times the far surface. Blur coverage and near radiance together; do not
   blur each side independently and then apply a sharp mask. Independent
   all-in-focus truth gives both layers their smallest PSF simultaneously.
3. Genuine coloured narrow radial filaments, focused at frame3, with the
   remaining observations blurred. These resemble the unwanted rays but
   belong in the truth. Losing them or neutralizing them must fail the gate.

Windows are fixed in original active-native coordinates, then translated by
the actual crop origin during scoring. Fan [138,133,171,167), glint core
[112,110,133,132), boundary strip [160,80,192,208), nearer real texture
[180,96,224,192), coloured radial detail [84,72,232,216). Flat uses the output
interior excluding 24 native pixels per side. No statistic is selected by the
candidate's own focus field. Positive PSFs have no clipped sensor samples.

Admission for one photographic replay requires, at EACH ISO:

- At least 5% lower fan-window RGB RMSE against independent all-in-focus truth.
- At most 10% increase in boundary-strip RGB RMSE.
- At most 10% loss of recovered true signal in the glint core, nearer texture
  and coloured radial detail. Fit each output channel against its centered
  clean truth template; compare positive in-phase recovery capped at 1.0 so
  removing manufactured contrast is not penalized. A baseline below 0.5 does
  not establish recovered signal; the nearer-texture and radial fixtures must
  actually exceed that threshold in every channel to support admission.
- At most 25% increase in both flat RGB RMSE and flat R-G/B-G error RMS.
- Coloured radial RGB and chroma truth errors must not rise by more than 10%.

The baseline must actually show the unwanted fan: its fan error must exceed
twice the flat baseline RGB error, and the noiseless out-of-focus observations
must contain fan-window energy absent in truth. Actual finest-band selection
must occur in the depth scene. Failure to exercise these conditions is a
diagnostic failure, never permission to relax a bar or tune the scene.

Commission the scoring with exact truth, half-amplitude, neutralized-colour,
and 1.4x-contrast outputs. Exact truth must score zero error and unit recovery;
half-amplitude and neutralization must be rejected; returning overcontrast to
truth must preserve the capped recovery. RGB error can improve by smoothing,
so it is paired with real-component recovery. Template recovery can credit
unrelated correlated patterns or excess contrast, so it is capped and paired
with absolute RGB/chroma truth errors. No gradient or chroma-high-pass score
is evidence of quality. Flat error is a same-domain known-truth spatial error,
not an estimate claimed interchangeable with sensor temporal sigma.

Direct band1+/base accumulator equality permits omitting the earlier proposed
coarse-only scene: that branch is now unchanged arithmetic. Final developed
pixels can still differ through the finest band and InputRange limiting, so
the depth/colour controls remain necessary. Save all failures and individual
ISO decisions. Passing synthetic controls admits one real-stack comparison;
it is not photographic acceptance, a default promotion, or a SOTA claim.
