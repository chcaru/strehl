# Upper-right background streak: two-frame cause inspection

One visibly isolated dark streak is present in the saved corrected coffee-bean
render. This was independently confirmed at1:1 in view-1/top-right.png; both
ends are visible, unlike the partly cropped top-left mark. Nominal output
centre is(6280,160), full-reference native centre(6404,242) after crop offset
(124,82). Independent conservative full-reference box:(6310,164,196,160).
These are visual nominations, not a physical dust diagnosis.

Fixed inputs: original coffee frames0 and104 (DSC00016.ARW, DSC00120.ARW),
using the exact prior metadata-bound input paths. Native ROI(6000,0,704,512).
Fixed scene/sensor context(6282,114,256,256); prove held map supports both
endpoint locations inside the source ROI before decoder execution. No alignment
fit, Lightroom TIFF, new calibration, correction map or whole-stack render.

Read the original active u16 codes using rawpy with its copy INSIDE the live
context. Independently decode the identical ROI using the held existing M61
caller executable (no LGPL source read or new build). Require byte-for-byte
agreement of all720896 payload bytes and every CFA phase before interpretation.
Reject on a decode mismatch, clipping/layout ambiguity or insufficient coverage;
never silently reduce the compared area. Retain original file metadata before
and after. This is not a whole-corpus read-only hash audit.

Views retain original green samples, one pixel per plane sample, with spatial
positions labelled. First use the same fixed black-subtracted range[0,14848]DN.
A second inspection-only stretch may use one pooled2/98percentile range for all
panels, explicitly recorded; never per-panel normalization. No spatial/temporal
noise estimate or statistical claim from this pair. Persistence at a sensor
location would be descriptive evidence, not proof of physical dust or an
approved correction. The prior correction's variance limitation still applies.

Root executes after source freeze; implementer never executes this allocation.
Different reviewer checks decoder agreement and inference choices. Reuse the
existing Windows Job runner; four decoder children plus one small analysis,
30wall/30CPU seconds per child,1GiB commit,60aggregateCPU seconds and32MiB
retained artifacts. No automatic retry or extension. Stop after cause inspection
and choose any intervention separately. Original corpus remains read-only.
