# M194c fixed baseline comparison

2026-09-07, before the candidate build and rendered outputs. Root owns this
comparison; roadmap_audit independently checks the reads and new bindings.

Use the exact forty M194b inputs, settings, crop, masks, targets and scorer
committed at `444eb759be0358cda25e97d4375f977a039efe6a`. Change only the probe
destination traversal and test code. Retain both ideal and optical-observation
targets and both the full-nine and original-frame-four comparators. The single
arm keeps its existing local-zero probe index. Do not regenerate input noise.

The original M194b build, driver, matrix runner and scorer remain byte-unchanged.
Build with their exact command and retain their normal source map. Additional
M194c Rust test includes live outside that map: bind them separately with this
controller, comparison code, both author/root preregistrations, all top-level
M194c Rust files and the legacy receipt,
copy their exact bytes before build, and require unchanged hashes after each
operation. The supplementary receipt binds build, run index and score hashes.
It supplements the frozen reader; it does not claim the original reader checks
the new external test includes. Assert those includes actually occur in the
gatefloor source and match the frozen M194c Rust source set before the build.

Read every candidate TIFF through the commissioned reader. Report pixel changes
against the baseline, every existing error/noise result, paired across-version
whole-image-repeat MSE differences and delete-one-repeat variance differences.
No pooled quality winner, physical calibration or SOTA admission follows.

Prospective engineering review triggers, fixed before output:

- An increase above 1 post-WB DN in any whole-ROI channel RMSE (including every
  noise-off and noisy output) requires an explicit regression disposition.
- A temporal-variance increase above 2% in any flat/plane channel and either arm
  requires the same disposition; show paired uncertainty, not pixel-based SE.
- Loss above 1 DN in any noise-off plane wave amplitude requires that review.

These are conservative engineering triggers, not independently calibrated
quality tolerances or new SOTA bars. All smaller changes remain reported. Blur
can improve noisy MSE, so noise-off waves and error to both targets remain
mandatory. The existing finite sampling/margin rule still applies to a quality
ranking. A layout-invariance repair can be accepted without calling its small
numerical movement an image-quality improvement.

The supplemental binding must refuse a changed or omitted included source and
accept unchanged files. The across-version comparison must give exact zero
under a same-output placebo and detect a separately added offset. The existing
M194b blur/color/noise controls remain the scorer's commissioning; duplicating
those controls does not create independent corroboration.
