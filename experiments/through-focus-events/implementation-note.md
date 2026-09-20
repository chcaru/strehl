# Frozen measurement interface

`source-traces.rs` provides ignored test
`merge_cmd::through_focus_events::vitamin_c_complete_source_traces` and reads
`STREHL_THROUGH_FOCUS_EVENTS_OUT`. Root owns the sole CLI include and execution.
The author did not build, test, decode RAW, or inspect measured traces.

The fixed exporter reads the same seventy originals once, in index order0..69,
and calls the retained full-domain `BandWorker::fold` with the same source index,
map, crop, actual rounded GPU/MHC/Catmull gather, optical profile and injected
guide noise as the old witness. One current worker/source is live. Each original
source remains u16. There is no retained aligned-image stack or final image.

For each original CFA plane sequentially, public `Pyramid::build` forms L0 on
the entire3460x2306 output-quad domain. Only G0/G1 are required: deeper Gaussian
levels do not enter L0's exact build. Production
`correction_variance_diagnostic::energy` forms smooth5(L0 squared). Fixed
row-major f32 sums emit the18 regions at original/+1quad-x, four planes each.
Parity origin[28,19] identifies active-reference global quad checkerboards.

`receipt.json` contains `roi_specs`, `shifts_quad_xy`, all geometry and source
bindings, plus `sources[70]`. Each source carries its active-u16/full-known4/
guide/variance hashes, beta, transform bits, and `rows[36]`. Each row contains
`roi_name`, role, shift, output/reference coordinates and four `PlaneSummary`
records. Records contain signed DN/L0 means, mean energy, two parity counts and
signed subset means, plus descriptive guide/guide-variance means. No temporal
derivative, fit, source index election, confidence or image-quality score is
computed by this exporter.

Before and after summaries, original-u16 and actual known4/guide/variance hashes
must be unchanged. Sources25/28/33/69 must also reproduce the old full hashes,
beta bits, and exact512-square known4/guide/variance file bytes. The retained
wide receipt and original-headroom receipt are hash-bound. Original clipping is
established only in the old broad core boxes at those four sources; other
sources/boxes remain unknown. Guide variance is never presented as four-plane
covariance. The background and translated boxes are spatial negatives, not
certified flat or independent noise realizations.

The independent control include checks direct enumeration, signed values,
parity, translation, invalid inputs and immutable arrays. These are arithmetic
controls, not evidence of optical identification. The separately frozen
independent analysis plan governs interpretation. No original file or frozen
earlier experiment is edited.
