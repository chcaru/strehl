# Independent plan: fixed StackMFF V4 pilot

Frozen before inference, 2026-09-25. Root runs the pilot; this reviewer owns no
model, download, inference or source-selection implementation. This is one
three-source, 384-native-pixel headroom observation, not a full-stack quality
or speed qualification.

Use only the existing donor112, donor152 and donor320 TIFF cores at delivered
coordinates `[3230,3000,384,384]`, in that order. Baseline is a comparison,
never an extra model input. Bind complete input TIFFs, their source-pure
receipt, exact RGB16 crop bytes, upstream commit/files and checkpoint. Keep
the same recorded development, reference244 geometry and display encoding.
Document the official grayscale conversion, quantization and normalization;
do not silently change them for linear RAW, apply another tone curve, resize
or tune contrast. Output must copy all three RGB16 channels from one original
input at the same pixel, using the categorical map. The model selects captured
RGB; it does not recover new radiance or implement native-CFA fusion.

Root's pre-run adaptation is explicit: RGB16/65535 followed by OpenCV RGB2GRAY
replaces the official quantized 8-bit loader. This holds developed encoding
while retaining precision; it is not a bit-exact replay of that loader. Skipping
discarded ImageNet constructor initialization is acceptable only with a strict,
complete checkpoint load and immediate restoration of the original factory.

Before interpreting the photograph, commission only these compact controls:

- Actual-model identical-source and constant-source cases, finite/valid
  integer map and exact selected-input RGB identity. Equal-input index ties
  may change labels without changing the image. Passthrough identity is
  mechanical, not image-quality evidence.
- A prescribed mixed map covering all three sources checks reconstruction
  indexing at known spatial addresses. A swapped-source or shifted-index
  mutation must fail this check; identical inputs alone cannot detect that
  error.
- The fixed reversed input order, with labels mapped back to original donor
  identities, reports both map disagreement and RGB disagreement. Preserve
  any discrepancy; do not pick the more favorable ordering or obscure changed
  pixels behind an equal label histogram. This checks the published order
  premise, not focus correctness.

The visual choice was made from the existing whole baseline and all three
native cores before model output. Donor112 supports the shorter, brighter
lower-right fan tips; donor152 supports the longer, slanted strands toward
the upper-right/central fan. Follow-up needs both groups retained, with a
plausibly cleaner contact than the current baseline and no conspicuous new
selection seams, color fringes or grain in the smoother surround. Losing faint
captured strands, darkening the region or merely beating the blurred donor320
is failure. Donor320 demonstrates visible hair loss; selecting it somewhere
in the smooth background is not automatically incorrect. Counts of selected
sources, map smoothness and scalar sharpness are not quality gates. Smooth
surround appearance is not a temporal-noise measurement.

The complete488-source baseline also contains fine loops and intermediate-focus
detail absent from both focused pilot donors. Their absence in the three-source
output cannot identify a learned-selection failure: that radiance/detail is
unavailable to this pilot. Report separately loss of a detail visibly supported
by112/152, seams introduced by selection, and missing coverage relative to the
complete baseline. Only the first two directly test this selector on supplied
evidence. A follow-up still needs all488 sources and a complete output.

Retain the entire384 result and compare all four original cores plus candidate
at native scale. The outer two RGB pixels of the source-pure cores may contain
MHC contributions from the old surrounding ring; do not claim pure-source
fidelity there. Cropped inference also lacks real context outside384. Excluding
two border pixels addresses MHC support only, not the network's receptive
field or a whole-image tiling seam. No recentering, alternate crop, donor search,
postprocessing or parameter sweep follows this result.

The [official V4 description](https://github.com/Xinzhe99/StackMFF-V4) identifies
it as GMFF's deterministic first stage. The [primary GMFF paper](https://arxiv.org/abs/2512.21495)
separates that stage from generative restoration. Published two-stage quality
claims therefore do not qualify this deliberately diffusion-free pilot.
A positive pilot licenses consideration of a separately bounded full route;
it is not an improvement deliverable to the owner. Any later improvement claim
must include the complete stack output and full-resolution master. A negative
closes this fixed model/ROI trial, without proving all learned methods fail.
