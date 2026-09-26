# Independent illuminant controls

Frozen before compilation/execution, 2026-09-25. Four ordinary tests in
`illuminant_aware_color::independent_controls`; root executes them. No RAW,
build, render or numerical gate was run by this reviewer. The operator author
must independently read these control choices. There is no photographic
quality pass or automatic admission in this suite.

1. `independent_d65_equivalence_controls`: with an independently chosen
   non-diagonal camera matrix and the WB implied by D65, compare replacement
   against current production `camera_to_srgb` at neutral and off-neutral
   inputs (absolute matrix/output error below 2e-6). A different map with unit
   row sums demonstrates the live failure of neutral-only validation.
2. `independent_warm_colour_controls`: run the flat/noise control first via
   actual `Render::with_saturation(...).develop`. Eight balanced sign draws
   at 0.2, far below the sensor knee, are transformed by an independently
   evaluated XYZ/Bradford path. Allow 5e-4 relative variance error plus 1e-11
   absolute for f32 arithmetic. Report each baseline/candidate variance and
   their ratio; a color transform may legitimately change covariance, so a
   ratio above one is not an automatic quality failure. Next, five externally
   specified colored XYZ vectors go through an independent forward camera
   model and the actual `Render`. They are not made by inverting the candidate.
   Expected f64 output error is below 1e-11; stored f32/Render error below
   2e-6. Test neutral intensities, calibration-scale cancellation and live
   transposed-matrix, missing-WB-undo and appended-CAT destroyers.
3. `independent_interpolation_controls`: a prescribed reciprocal-temperature
   midpoint, both endpoints, out-of-range clamps, and invalid temperature,
   singular/nonfinite matrix and invalid WB refusals. This commissions the
   interpolation arithmetic, not the scene's assumed 3000 K coordinate.
4. `independent_metadata_refusal_controls`: valid synthetic A/D65 metadata;
   missing/duplicate/renamed A, mismatched selected matrix, direct-matrix
   ambiguity, wrong camera, invalid WB and singular calibration refusals.

Reporting is standard Rust test pass/fail plus one `ILLUMINANT_FLAT ` line
containing JSON with `candidate_variance`, `baseline_variance`,
`independent_expected_variance`, `candidate_baseline_variance_ratio`,
`propagation_relative_error` and `scope`. The root runner requires all four
exact names and parses this record. No `quality_pass` field exists.

The separate oracle uses partial-pivot Gauss-Jordan inversion instead of the
operator's scaled adjugate. Bradford numeric facts come from
[ICC Technical Note 02-2003](https://www.color.org/chadtag/); current core sRGB
and D65 definitions fix the output color-space convention. Synthetic camera,
white and patches validate algebra only. They do not calibrate the real Sony
sensor, measure the polarized light spectrum, or establish physical colors.

The cached experiment must independently require complete baseline RGB16/ICC
identity and pinned rewrite identity, with only the resolved final matrix
changed. The existing highlight rolloff implementation is held, but its
neutral-luminance calculation consumes that matrix; where active, its numeric
result can consequently change. This is part of the existing developer's
response to the matrix, not proof of a separately repaired highlight defect.
Whole images and genuine colored/bright native structures remain necessary
for the root's photographic review. Neutral fit, added saturation and fewer
white pixels cannot establish photographic improvement.
