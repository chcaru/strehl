# Native domain and existing gather clarification

2026-09-09. Root amendment2 to the source-only charter. No execution grant
or production policy change. The fixed27 original controls remain unchanged.

## Actual crop and depth

Root chooses one128x128 CFA-plane Crop at quad origin(1694,1108), conditional
on independent verification of the native7032x4688 active /3516x2344 quad
domain. These are active-local quad coordinates, not full decoded-buffer
coordinates or full-resolution RGB coordinates. Record actual active origin
and storage stride separately. Refuse unsupported metadata; never move the
crop after seeing pixels.

Keep configured DEFAULT_BANDS=7. Existing level_sizes stops before an extent
below8, so this Crop yields128/64/32/16/8, four Laplacian levels plus base.
The native exponent uses actualnb4. This is an opt-in Crop consumer diagnostic,
not a full-frame seven-band Scale-default certificate. Preserve all source-
derived versus observed support/phase/crop-border populations and beta
prefix/fallback. No scalar-white-gain promise at every crop pixel follows.

## Correction: native alignment already interpolates color internally

The original charter's phrase "no RGB conversion before the measurement" was
too broad for the current native placed-map route. Independent source review
identified the conflict; root verified align_cmd.rs::warp_frame_in_place and
warp_frame_in_place_fullres directly.

The full-resolution gather is enabled by default. It builds a black-subtracted,
white-balanced mosaic, MHC-demosaics temporary RGB channel planes, gathers
each CFA site's channel using the geometric transform plus applicable
chromatic-aberration correction, removes the working gain, and returns u16
site values to the native merge. The final full-resolution output demosaic
is therefore not the only interpolation stage in the current native route.
Root's earlier user explanation implied otherwise and was incomplete.

This amendment means: do not introduce an external developed-RGB input or
parallel merge for this diagnostic. Preserve and explicitly report the current
internal native gather/demosaic/WB/CA/quantization path. Do not disable
STREHL_FULLRES_GATHER or CA to manufacture an identity null or satisfy the
overbroad original sentence. Any future CFA-only/on-demand alternative needs
its own evidence and is not commissioned here.

"Placed identity" means geometric Similarity::IDENTITY, not an assertion
that every effective channel mapping is identity. Preserve actual capture
path, camera/lens identity resolution and effective CA/profile/gather settings.
R/B may have nonidentity channel maps; green identity must also be checked at
the actual consuming addresses. White-noise transfer cannot be inferred from
the geometric label alone. This is why exact original, post-gather and
consumed samples must remain distinguishable.

The full-frame temporary allocations and probe synthesis/warp remain in the
resource plan even though the downstream crop is small. One current native
frame plus sequential temporary copies is allowed; an aligned-frame stack
is not. No requirement to hide or remove existing processing for appearances.

## Interpretable outcome rather than an invented accuracy certificate

Root accepts a conditional finite diagnostic. Five paper repeats and an
input-only nuisance screen do not supply independent physical motion and
illumination truth. Freeze two disjoint paper contrasts with a separate signal
witness and an all-five sensitivity check if independently justified; preserve
the22-frame dark inference separately. A paper premise refusal need not erase
an interpretable dark comparison.

Report conditional uncertainty and dependence, actual gate operands and the
dark pre/post-clamp transfer. No unconditional physical-model PASS, fixed
photographic noise benefit, new profile fit or SOTA claim is required from
this population. Do not manufacture spatial degrees of freedom to obtain it.
