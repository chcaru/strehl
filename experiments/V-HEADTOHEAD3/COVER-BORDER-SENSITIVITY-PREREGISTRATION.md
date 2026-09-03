# V-HEADTOHEAD3 — conservative central-site cover sensitivity

**Frozen after the corrected linear profile, before recomputing any filtered
cover statistic.**

## Why this is needed

The matched camera-linear four-cell profile corrected the sRGB output-space
error but still failed its mandatory specificity predicate.  Scale, which has
no crop-fill boundary, returned a nominal 640-plane-pixel stable tail rather
than 8; Crop returned 320.  No black-fill reach is therefore admitted for
`113MSDCF`.

The profile also exposed a unit error in schema 2: profile distances are on
the binned camera-linear plane (`3516x2344` / `3448x2298`), while the existing
ordinal sites and their 256-pixel clearance are on the full-resolution sRGB
renders (`7032x4688` / `6896x4596`).  The exact conversion is two output pixels
per profile-plane pixel.  Schema 2 already returned `existing_rois_clear=false`
because specificity failed, so this error did not reverse its disposition,
but the field comparison must be corrected.

## Fixed sensitivity

This is a conservative sensitivity analysis, **not** a relabelling of either
nominal tail as black-fill reach:

1. Use the original frozen PMax0 site list and hashes; add no sites.
2. Repeat the already commissioned, image-fitted Scale and Crop mappings.
   The comparison scale `s` remains fitted independently from image content,
   never inferred from dimensions or from cover `k`.
3. Retain a paired site only if all original registration/rail/bounds gates
   pass **and** the complete Scale patch is at least
   `2*640=1280` sRGB pixels from its emitted border and the complete Crop patch
   is at least `2*320=640` pixels from its emitted border.
4. Require at least 12 detail and 6 flat sites.  Do not replace exclusions.
5. Recompute only the licensed 0.10–0.20 cyc/native-pixel PMax0 quantities,
   bootstrap seed `20260903` for detail and `20260904` for flat, the four
   quadrant signs, and leave-one-site guard.

If counts fail, the original 256-pixel `COVER_NOT_CAUSE` result is downgraded
to `BORDER_UNRESOLVED`.  If counts pass and the crop/default interval remains
inside `[0.98,1.02]`, report the registered causal label only as a **central-site
ordinal band-power sensitivity**.  It is not resolution, MTF, or evidence that
Crop recovered scene detail.  The nonspecific border profile remains
unresolved in either branch.

Bias is toward retaining `COVER_NOT_CAUSE`, because that is the published
result this sensitivity can preserve.  The output/plane conversion is checked
against exact paired dimensions; omission, inversion, or a one-pixel threshold
mutation must go RED before the filtered real values are accepted.
