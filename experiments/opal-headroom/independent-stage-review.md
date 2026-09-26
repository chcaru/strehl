# Independent stage-observer review

Status2026-09-25: ready for root's generated controls and unchanged-cache
observer replay. This reviewer ran no RAW job, Rust build or stage observer.

Read stage-observer.rs against actual write_demosaiced, Render::develop,
clip_highlights, saturation_ceiling and default MHC dispatch/stencils. The
observer receives the actual normalized, white-balanced full mosaic and actual
resolved development. It calls the same full-context MHC and renderer helpers,
records the explicit stage sequence, and requires current and shoulder complete
pixel hashes to match their retained writer outputs. Observer-off/on complete
TIFF identity, development identity and input cache/original artifact hashes are
required. These checks are stronger than a read-only argument, but remain
unexecuted at review time.

No arithmetic defect identified in the reviewed path. The observer is test-only
and inactive by default. Its two frozen native rectangles remain the original
targets. Holding the global observation mutex for the scan changes observation
cost, not image arithmetic; no performance claim should be made from that run.
The no-override check keeps the5x5 MHC support applicable. A later different
demosaicer must not silently inherit that claim.

The support inference is carefully one-sided. If a post-MHC camera channel
reaches its per-channel container ceiling while **every** one of the25 merged
CFA samples in the complete support is strictly below its own CFA-phase ceiling,
the ceiling crossing is introduced between those merged samples and that MHC
output. This does not show original RAW clipping, sensor saturation, physical
ground truth or that the interpolation is photographically wrong. The merged
inputs already contain gather/selection effects. Conversely, one support value
at or above its own ceiling makes this diagnostic inconclusive; it does not
prove that value caused the RGB crossing. The complete25sample square is a
conservative superset of individual MHC channel stencils, which makes the
positive implication safe but can undercount it.

The nominal ceiling here is the pipeline's container maximum carried through
black subtraction, range normalization, white balance and exposure, rather
than a newly measured sensor full-well threshold or the tone white anchor.
The observed mosaic shares those units. The fixed crop has even native origin
[120,80], so local RGGB phase agrees with the normalized writer mosaic.

Added one cheap independent control in independent-stage-controls.rs. An exact
ceiling equality must count as a pin while changing no clipped channel;
one-ULP-below and one-ULP-above cases distinguish predicate from action. A
separate unequal-ceiling RGGB fixture checks all four phases at half their own
ceiling, at equality and one ULP below. This would reject mistakenly using one
green/global ceiling or classifying a green phase as red/blue. The author's
existing actual-MHC positive and flat negative remain necessary to demonstrate
that the crossing mechanism can occur. Root must run all three tests, with an
actual compile line; the independent test is prepared, not yet executed.

Pin/clip/rolloff/white counts explain pipeline activity only. None is an image
quality score, RAW-recovery count or reason to make an output darker. A useful
change still needs distinct preserved reflection structure, the protected
colour texture, the complete output, and an independently judged improvement.
