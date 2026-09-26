# Frozen independent transfer screen

Prospective, 2026-09-26. Frozen from fixture source definitions before this
reviewer opens any new exported pixels or candidate result. Owns only this plan
and `independent-transfer-check.py`; first-fit sources, scores and decisions stay
unchanged. The19 known cases remain developer regressions, scored separately.

Scope: the10 fresh cases in the independent heldout manifest. FreshColour-v2
replaces the earlier planned Compound case; count10 is unchanged. It supplies
new positions/rotations and R/G/B amplitudes.065/.004/.050, not a previously
unseen colour family. New compact pupil/subject/geometry and independent per-case
noise augmentations remain generated evidence, not calibration of the actual
optics or camera. Seven-band cases are analytic planar support/scale probes;
their mostly separated carriers do not prove competing-depth occlusion handling.

## Windows fixed before pixels

All compact coordinates below are half-open source-native `[x0,y0,x1,y1]`.
Subtract the export origin `[16,16]` exactly once when indexing output arrays.
Every compact case uses interior `[30,30,162,146]`, except the clipped case's
unqualified core: score only its two protected windows below. No automatic
recentering, texture ranking or window change follows qualification or scoring.

| Family | Additional windows / purpose |
| --- | --- |
| forked-filaments | `[63,43,134,137]`, nominated RGB positive |
| serrated-polygon | `[83,43,122,137]`, contact/near/far preservation |
| near-fine-far-coarse | `[64,42,131,138]`, nominated RGB positive |
| unclipped-glint | core `[79,75,104,99]`; adjacent `[128,49,156,134]`; spread `[103,71,117,112]` |
| clipped-glint | adjacent `[128,49,156,134]`; spread `[103,71,117,112]`; no core recovery claim |
| weak-colour | `[43,36,110,144]` for the four weak-green ellipses; `[118,47,131,129]` for far-colour line |
| flat | interior only |

Seven-band flat and multiscale cases use output-native interior
`[floor(W/4),floor(H/4),floor(3W/4),floor(3H/4)]`, where W,H are output-native
dimensions. Multiscale additionally uses one fixed square per carrier j=0..7.
Its centre is `((W+32)*(.15+.23*(j mod 4))-16,
(H+32)*(.30 if j<4 else .70)-16)`. Half-width is160 native pixels for j<4,
300 otherwise. Bounds are `floor(centre-half_width)` to
`ceil(centre+half_width)`, intersected with the output domain. Do not move a
boundary to obtain better recovery.

Independently reconstruct each carrier's truth template from the declared
Gaussian-windowed cosine: wavelength `4*2**j`, envelope sigma70 or170,
angle`.23*j+.11*variant`, phase`.31*j`, RGB amplitude[.040,.034,.044], and
truth PSF sigma.7. Verify their sum plus.25 against the exported truth within
1e-5 absolute camera-RGB (a fixed f32/transcendental tolerance). Score each
carrier separately with all other true components subtracted, so retained coarse
energy cannot hide loss of the finest carrier. The exporter now samples both
focus depths.22/.78 exactly; the prior schedule that erased the finest source
signal was corrected before any export or candidate read.

## Qualify first; assess a frozen model separately

`qualify --dataset HELD --out DIR` reads native canonical/uniform/truth and
independent base/near/far templates. It checks flat cases first, fixed support,
truth decomposition, exact truth acceptance and live detail/noise/core/colour
destroyers. It may report an unqualified component or positive; it cannot
replace it silently. It creates no model prediction and is not a learned result.

Reuse the earlier RGB/green/chroma RMSE and centered component-projection math.
Recovery eligibility is unchanged: template standard deviation>=.001, separated
near/far system determinant ratio>.05, and current recovery>=.5. Credit is
capped at1.0. An unavailable or weak baseline is unqualified, not candidate harm.
Required protected evidence is near and far on the thin case, the genuine glint
core, red and blue near detail on FreshColour, and every seven-band carrier in
at least one colour channel. Record all other eligible guards too.

Both nominated positives require nonzero current error and uniform RGB error
at least1.05 times current error, so a gain supplied by plain averaging cannot
nominate this model. This is a viability check against that shortcut, not a
matched-noise significance claim; these fresh flats are not matched ISO/N/level
twins of every structured case. Independent component/noise destroyers must be
exercised and rejected before accepting the relevant score as informative.

`check --dataset HELD --qualification QUALIFICATION --predictions PREDICTIONS
--weights MODEL --commission GENERIC_NATIVE_RECEIPT --out DIR` requires the unchanged qualification binding and a
model frozen before challenge inference. Verify model/prediction/data bindings,
all source/band weight shapes, finite positive denominators and complete
reconstruction from saved weights through the commissioned generic consumer.
The consumer's separate native commissioning must cover odd seven-band support.
Fresh truth is evaluator-only: the predictor's infer path must not load it.

Prospective bars stay those declared in independent-plan.md: flats<=1.10 of
both current and uniform; qualified structured RGB/green/chroma<=1.05 current;
each eligible component>=90% of capped current recovery; both nominated positive
RGB errors<=.95 current. Uniform remains a reported structured comparator.
Report absolute errors, all ratios, every failed window and every unqualified
required protection. Do not average a failed core/carrier into a passing image.

Lower image error can reward smoothing/desaturation; independent component
preservation opposes that failure. Projections can reward ringing, broad common
structure or correlated errors; absolute RGB/colour errors and per-carrier
guards oppose it. These controls bound those failures without certifying real
photographic quality. Flat noise drawn from the same injected model does not
calibrate that model. Slight reconstruction tolerances are arithmetic bounds,
not adjustable image-quality bars.

The checker reports mechanical status, qualification coverage and prospective
scientific status separately. No automatic production promotion follows. A
fully qualified pass supports the separately scoped complete488-source marigold
observation. A narrowly failed or unqualified conjunction stays visible and needs
the independent written observation rationale already required by
independent-plan.md; no unreviewed preservation harm or hidden case deletion.
Keep full matched development and complete output for any photographic gain.
