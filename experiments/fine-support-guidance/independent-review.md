# Independent review: fixed fine-support diagnostic

**Source review complete; execution pending.** This measurement does not merge
a candidate image or establish image quality. It asks whether one fixed pooled
score changes the preference observed at six locations fixed before the trace.

The authored API reads the actual production level0 Laplacian and energy
kernels through the existing diagnostic bridge. Its floor has the production
multiplication order `gate * beta0 * variance`; its 65x65 box separately pools
energy and that floor before positive excess and normalization. It does not
silently reuse a coarse-band beta or pool exponentiated weights. The exported
ratio preserves the production one-DN-squared denominator guard. Zero-score
ties are reported, and an arg mismatch against the earlier actual weight dump
requires investigation because exponent clamping can create additional ties.

The real-data path consumes actual full-domain BandWorker luma, variance and
measured beta. It extracts even-origin **quad** rectangles with 48-quad padding.
The level0 reconstruction has at most four-quad source reach, energy smoothing
adds two, and the new pool adds 32: 38 quads total. Thus the selected samples'
greater-than-40-quad margins cover the local operator, and their even origins
preserve the original level0 decimation phase. These are source-derived support
statements, not inferred from agreement between two numbers.

One generated control was frozen for root's build. It compares an asymmetric
even-origin crop with the full field and requires a deliberately odd-origin
crop to disagree. It checks the actual kernel seam, independent direct box
sums, known constant-field behavior, common input scaling, unchanged source
arrays and explicit invalid-input refusal. `independent-plan.md` records the
fixed numerical tolerance and failure examples before execution. No radius
sweep, camera calibration assertion or image-quality threshold was added.

Frozen controls SHA256:
`f9c00c454222ba923d372405ea89b11121e5dc07be4f8cedf81ac74b8950f2e6`.
Plan SHA256:
`fa4488b40a172db7a77a861b6e4cbba2eab4d5f93679882285ddc965bd38ab51`.
Filter: `merge_cmd::fine_support_tests::independent_controls::`.

The preceding exact-ancestry trace is retained in
`quality-september19/vitamin-c-weight-trace-review-1/review.md`. Its important
constraint remains: the dark fan's known-green band0 coefficient already gives
frame69 a 0.956702 weight share. Pooling must change that preference; merely
carrying current finest-band weights upward could spread the same error. The
large support can also borrow focus from a neighbouring depth, which requires
a subsequent depth-step and true-colour quality control if this diagnostic
supports implementation. A passing operator test alone cannot admit it.
