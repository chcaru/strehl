# Independent review: upper-right background follow-up
Status: source-only ready; no RAW decoder or numerical inspector run by reviewer.
The nominated rendered mark is visible at1:1; physical cause remains unproved.

- Fixed inputs are coffee frames0/104, original metadata-bound ARWs only.
  The held map is reference52 -> source, plane3516x2344, with its SHA checked.
- Independently decoded map hex coefficients and evaluated the native affine
  matrix on context corners, without calling the author's sampler:
  frame0 bounds x6343.078..6606.385, y57.576..320.883;
  frame104 bounds x6228.678..6478.629, y156.751..406.703.
  These conservative inclusive-upper corners fit RAWROI6000..6704,0..512.
  Fixed sensor context and the target also fit. No pixel input was read.
- run.py calls fixed() before the first decoder launch. The two-pixel source
  margin in fixed() is stronger than necessary for the original-sample panels.
- rawpy copies raw_image_visible and pattern inside the live context; metadata
  values are captured there. The saved patch must be uint16 and512x704.
  No TIFF/Lightroom read occurs through the new primary entry point.
- Existing M61 caller dumps active-area y0=0,x0=6000,h512,w704. Analyzer demands
  the exact16-byte header plus720896 payload bytes per frame; all360448
  samples and all four parity phases must agree before either frame is viewed.
  The pair contains720896 samples, not720896 total payload bytes.
- Comparison receipts precede assertions; any mismatch or sensel>=15360 stops
  interpretation. Pattern RGBG/[[0,1],[3,2]] fixes the channel/phase convention.
  Black subtraction uses each phase's recorded channel black.
- Panel samples are original G1/G2, spacing2native pixels; there is no spatial
  resampling. Fixed0..14848DN and one pooled2/98 range are shared by all panels.
  The pooled stretch is inspection-only, not exposure correction or a metric.
- Endpoint display limitation resolved before execution: each256x352 phase panel
  now shows the full allocated704x512 RAW ROI without resampling. Actual phase
  origin/spacing and array shape are recorded; CONTEXT remains separate metadata.
  Both fixed and mapped target extents fit these panels. No extra decode was added.
- Final inspected source SHA256:
  23c07b674e9f89ec548b5c961a07de98211bb7475ac85b602b1e7131afaf0fb7.
- Original metadata are checked before/after; source/array/input hash bindings
  are checked in analysis. This is a two-file guarantee, not a corpus audit.
- Root's runner binds scripts/helpers/executable and records all five invocations.
  Each child has30wall/30CPU seconds and1GiB commit; aggregate60CPU and32MiB
  retained outputs are checked. Failure preserves receipts and stops, no retry.
- The old sampler/control population is reused, not recommissioned. No new map,
  calibration, correction, noise estimate or whole-stack render is included.
  Persistence in two originals would support a source contribution, not physical
  dust identification, noise-fidelity correction or a default policy.
