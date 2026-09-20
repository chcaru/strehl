# Independent full-adapter mechanical check

Frozen before execution. Parent runs one small Rust test
`merge_cmd::rb_residual_full::independent_controls::independent_rb_residual_full_mechanical`.
Output: `STREHL_RB_RESIDUAL_GUARD_OUT/mechanical.json`; marker
`RB_RESIDUAL_FULL_MECHANICAL`. No original RAW, image-quality inference or new
noise calibration occurs in this control. The generated admission remains false.

Use an asymmetric 31x23 quad field, odd quad crop origin, held warm WB, black/white,
matrix, exposure and tone. Change only red and blue with distinct spatial patterns.
The established phase-packed `camera_rgb` implementation is the independent
whole-mosaic oracle: demosaic baseline and candidate, then develop
`[candidate R, baseline G, candidate B]`. Demand exact new row-writer RGB16,
including native boundaries. Both the live R/B update and the deliberately wrong
uncorrected camera-green output must differ by more than 100 delivered samples;
otherwise the fixture has not exercised the new path. At least 100 camera-green
pixels must differ after MHC despite unchanged CFA greens.

Identity must equal the original `write_planes` TIFF after decoding all samples;
live TIFF must equal the independent mixed-camera oracle. Require identical,
nonempty ICC data and unchanged input arrays. NaN input and invalid WB refuse.
Verify the full N70/seven-band scalar threshold against the retained independent
SciPy reference. These checks can catch wrong phase/normalization, double WB,
missing camera-green authority, inert updates, and an incorrect cost population.
The pure threshold check does not exercise allocation of the full accumulator;
source review binds both cost and full constructors to that same N70 argument.

Actual full CA/rounded gather, source simulation, chunk means and seven-band
consumer are existing commissioned paths. Review their new wiring separately;
the parent must still run source35 cost with all 16 probes and exact single-source
CFA/RGB16 equality, followed by the historical full-baseline pixel guard before
any complete photographic interpretation. No universal/whole-image F-error claim.
