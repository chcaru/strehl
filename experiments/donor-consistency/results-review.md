# Independent photographic decision

**Close the exact fixed-mask recipe as an incomplete repair.** It provides a
useful positive result at the facet glint, but does not meet the joint goal at
the dark inclusion. Do not promote it or start automatic donor assignment
assuming this reconstruction is already adequate. This does not reject source
consistency in general: the late-source control makes its relevance visible.

I inspected all three complete overviews, the five canonical384-native windows,
and three additional views centred on the prescribed mask geometry: facet
[2533,2846,160,160], dark [3011,2097,160,160], and nearby structure
[3180,2010,120,120]. These additional views use3x nearest-neighbour replication;
unmarked images and separate radius16/24 outlines are retained. They expose
boundaries rather than hiding them. Helicon B uses the previously independently
checked coordinate transform, retaining its1.0107 scale difference.

## Image-grounded observations

- **Facet core/tails:** donor28 preserves a compact bright core and reduces
  both prominent left/downward coloured extensions. The lower bright contact
  and surrounding facet edges remain visible; this is not simply deleting the
  glint. Source28's retained native view supports the compact form. However,
  the replacement leaves diffuse cyan/grey residue beside the glint and does
  not reach Helicon B's cleaner compact appearance. The fixed late69 arm instead
  produces a larger blurred coloured bloom, demonstrating a live donor effect.
- **Dark core/tails:** the prescribed donor33 changes the upper dark/bright
  transition and reduces some narrow ray structure, but the conspicuous long
  cyan/pink downward tail remains. At3x it is still a major element of the
  image; Helicon B and the retained source33 view are substantially more compact.
  Late69 enlarges and blurs the feature further. Thus the positive-versus-late
  distinction is real, but improvement over a destroyer is not sufficient to
  pass this repair.
- **Competing donor25 structure:** the central diagonal/ridge junction and
  surrounding small structure remain in the candidate. The same-mask late69
  arm softens the central detail. The retained source25 view supports that
  structure. I see no gross collapse of this witness from Gaussian mask
  diffusion, and no clear additional detail gain is claimed.
- **Transition and noise:** I see no hard cut boundary or large discontinuity
  in the native windows. The facet's diffuse residual remains a limitation;
  its precise attribution to mask taper, retained coarse mixture, or source
  differences is not established by these views. The masks do not contain an
  independently calibrated flat-noise patch, so small-area selection noise is
  not quantified. Absence of a conspicuous grain increase here is not proof of
  noise-neutral selection.
- **Remote controls:** pale-background, fine-crystals and bright-facet are
  exactly unchanged in RGB16 for both candidate and late arms. They retain the
  baseline appearance and noise; this experiment does not provide the earlier
  green-match background improvement. The whole-image overviews show no broad
  transformation of the scene, consistent with a local diagnostic.

The successful facet control narrows the problem: source provenance can improve
this defect while retaining a compact core. The dark result shows that these
prescribed labels combined with these fixed Gaussian AC masks do not deliver
the full benefit already visible in a focused source. It does not identify
which remaining reconstruction or support choice is responsible. Preserve this
partial result and the failure; do not select a new radius, donor or band count
after inspecting it and relabel the same experiment successful.

## Verification and scope

The corrected generated controls passed in `controls-2/process.log`: independent
three-source mean base and off/zero/base checks are bit exact; all-ones finish
error is0DN with four actual clamp excursions; mixed coefficient maximum error
is0.00003052DN and reconstructed error0.00024414DN. The first failed run was the
test helper's missing per-frame cache reset, not a production defect; its failed
receipt and the new mean-base regression are retained.

The full-run completion receipt verifies unchanged originals/map and baseline
RGB16 identity. Candidate TIFF hash:
`ba57bb889a0dbe883e3fd889dffb831bbf7296d8f32730337ecde7f6123f2b48`.
Late TIFF hash:
`6635aee9c56f350e906b9add33453d1aab7e55b3f7e1ae03e80b4ba3b0b3fb6d`.

Independent preparation command:
`python -X faulthandler experiments/donor-consistency/independent-photo-review.py`.
Its `review-1/receipt.json` binds the images and coordinates. It found523457
candidate RGB16 pixels changed (about1.64% of the complete image), including
513912 outside the three native radius24 footprints. Most such activity may
be very small: these counts describe support, not visible damage or quality.
The changed bounding box is[2199,1677] through[3675,3324], inclusive. Coarse
Gaussian masks overlap from level4 onward, but the saved mask receipt reports
no sum-over-one normalization at any level. No mask was changed for this review.

The first preparation attempt refused an unprofiled Helicon convenience PNG
before making boards; the completed preparation reads its original RGB16 TIFF.
All displayed arms then have the same embedded sRGB profile, with unchanged
sample values apart from rounded RGB16-to-RGB8 display conversion. The focused
source witnesses are retained developed-image crops, not RAW truth or perfectly
registered pixel comparators. Source25 was re-extracted from the existing
developed TIFF using its retained crop receipt and matched its saved RGB16 hash;
the command and receipt are under `review-1/source25.py` and
`review-1/source25-receipt.json`.

This remains one externally labelled local counterfactual on one70-frame stack.
It is neither an automatic algorithm nor an all-image/SOTA improvement, and no
new sharpness, gradient or aggregate photographic quality score was used.
