# Independent fixed focus-front prediction test

Frozen before generated or photographic execution, 2026-09-25. Root executes;
the model and extractor have separate authors. This reviewer owns the control
choices and prediction bars. No original RAW, merge treatment, native consumer
or candidate photograph is authorized by this proxy test.

Read SYNTHESIS §3.4.2 and the relevant M67/M73, M70 and M145 records and source
reports. Structural smoothness does not establish focus correctness; frame
ordinal is not calibrated depth. Multimodal profiles and finite spectral
support remain live failure mechanisms. A Gaussian response and one shared
width per band are rejectable approximations, not a measured lens PSF. In
particular, different tile texture spectra can violate a shared band width even
on a true plane. A poor fit therefore does not establish nonplanarity.

Use all 299 existing, identically developed chip TIFFs and the exact source map
in reference149 gauge. The extractor preserves the frozen 35 grid sites plus
seven existing native witness centers; it chooses none by image content.
All 192-square filter supports must be disjoint and valid at every source.
Only the central 128 square contributes DoG powers at sigma pairs (1,2) and
(4,8). These toned-RGB, interpolated, CA-off contrast powers differ from the
current CA-on native CFA consumer. No temporal filtering, noise subtraction,
rectification across sources or local peak election is allowed.

Spatial training consists only of grid sites with
`(row//2 + col//2) % 2 == 0`: 19 sites in five two-by-two blocks. The other
16 grid sites in four blocks and all seven named witnesses are held out.
Band0 training curves fit the plane and seven-knot monotone nonuniform
schedule. Band1 may fit one width on the same spatial training sites while
holding the plane and schedule fixed. No held site fits a location, width or
schedule. Its nonnegative amplitude and free offset use even ordinals only;
odd ordinals are scored. The competing constant is also calibrated on even
ordinals. The second band shares source images and is not statistically
independent noise evidence, but its held-site response is not used to fit
the geometry it tests.

The following bars apply unchanged to generated and real profiles:

- Informative support requires `(q90-q10)/max(abs(q90),1e-12) >= 0.15` in
  both bands, using even frames. At least two sites in every training and
  held grid block, and all seven named witnesses, must meet this condition.
  This is observed temporal modulation, not SNR or physical focus truth.
- On informative held sites, each band's aggregate RMS error relative to
  the calibrated constant predictor must be at most 0.50. The 90th percentile
  of per-site ratios and each named witness ratio must be at most 0.75.
  Each held grid block's aggregate ratio must be at most 0.65.
- Both fits must converge without an active registered parameter bound.
  Numerical completion cannot override prediction or coverage failure.
  Insufficient modulation, numerical refusal and wrong profile prediction
  are reported separately. No flat site earns admission through tiny absolute
  residuals, and no apparently good overall average can conceal a bad witness.

RMSE may reward suppressing structure when noise dominates. The modulation
and constant-predictor comparisons limit that failure here, but do not turn
contrast-profile prediction into image quality. These are predictive proxy
bars only; no sharpness, radiance-fidelity or noise-reduction claim follows.

The small generated set has 97 frames on the fixed 42 coordinates. One true
plane uses a nonuniform seven-knot schedule with increments
`[.07,.11,.14,.19,.21,.28]`, spatially varying amplitudes/offsets and independent
fixed proxy noise. **Its positive exactly shares the fitted Gaussian family.**
The two widths (.050,.035) deliberately differ but are not physics-ordered
predictions of the extracted bands. This positive commissions fitting and
cross-band parameter separation only; it cannot validate physical adequacy
or injected sensor calibration.

An exact flat must refuse fitting; a noisy flat must fail modulation coverage.
A true two-dimensional bowl depends on `x*x+y*y`; it cannot be recast as a
monotone warp of one planar projection. A two-depth case supplies two equally
weighted lobes separated by .28 in the latent schedule. These two cases must
have coverage yet fail actual predictive bars: optimizer refusal alone is
not a successful falsifier. Separately, shift the positive model's plane by
.25 and reverse its two spatial slopes, each with its schedule and widths
held. Both smooth-but-wrong predictions must be rejected; no refit can absorb
the sabotage. No parameter sweep, alternate initializer or relaxed bar follows.

Three extraction controls precede photographic TIFF access: hand-specified
complex mapping with nonunit scale/rotation and the real crop/quad convention;
source/channel-coded integer RGB sampling with axis/shift destroyers; and
constant versus two-frequency spatial signals through the actual DoG code.
Constant power has a fixed 1e-12 rounding allowance. These commission indexing
and finite-filter arithmetic, not contrast quality or fractional-sampler truth.

Root command for generated commissioning is
`independent-controls.py --model model.py --out <fresh-result.json>` under
the bounded wrapper. All five case fits and both wrong-front decisions are
retained before any refusal exit. A passing real result would establish only
held-out prediction by this finite proxy family and require a separately
frozen native-consumer hypothesis. A negative does not license reselecting
tiles, adding knots, changing response families or calling the chip nonplanar.
