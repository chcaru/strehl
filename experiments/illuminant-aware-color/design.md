# Fixed illuminant-aware developer experiment

Pre-code design, 2026-09-25. Root authorizes this new experiment-owned module,
independent numerical controls, metadata from exactly the first original of
opal103 and marigold4, then one complete cached writer pair per subject. Root
owns compilation/execution. No shared/default or currently bound source changes.

## Formula and interpretation

Current development is already a camera-space von Kries approximation, not
an unadapted image. It uses as-shot WB before MHC and a neutral-preserving
daylight matrix afterward. A D65 label or an omitted-CAT comment does not
demonstrate a photographic error. This replaces that final matrix; it does
not append an adaptation to the old one.

Let W=diag(wb_R,1,wb_B), n=W^-1[1,1,1], and C be XYZ-to-native-camera RGB.
For the declared shot-temperature coordinate T, interpolate the A and D65
calibrations with warm fraction
`a=clamp((1/T-1/T_D65)/(1/T_A-1/T_D65),0,1)` and
`C=a*C_A+(1-a)*C_D65`. Fixed nominal endpoint temperatures are 2856 K and
6504 K; these rounded calibration coordinates are stated, not a fitted CCT.
The photographic coordinate is exactly 3000 K, grounded in the owner's
manual-WB setup and explicitly an experimental assumption. It is not a
measurement of the light spectrum or an inferred scene neutral.

Set q=C^-1*n, y=q_Y, and w=q/y. With B the Bradford cone matrix,
`CAT=B^-1*diag((B*D65)/(B*w))*B`. For the already-WB MHC input v, the replacement
is `T_out=XYZ_to_sRGB_D65*CAT*C^-1*W^-1/y`, then `T_out*v`.
The inverse W prevents duplicate WB; y preserves the current unit-neutral
brightness convention. Under the same C with its implied D65 WB this reduces
to the current row-normalized matrix, including off-neutral colors.

Primary reference: [Adobe DNG1.7.1 pp100–103](https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section_733958301/download-1/DNG_Spec_1_7_1_0.pdf).
It distinguishes matrix interpolation, camera-neutral inversion and the
no-ForwardMatrix adaptation path. This is a narrow ARW consumer experiment,
not a full DNG implementation. It treats the exposed decoder matrices as
XYZ-to-the-same-native-camera coordinates as the samples, as documented by
our Frame API. Separate AnalogBalance, CameraCalibration and ForwardMatrix
are not exposed. Their absence from Frame is not proof that their physical
effects are absent; no synthetic test calibrates the real sensor.

## Data availability before implementation

`strehl_raw::decode` directly copies decoder wb_coeffs and each named 3x3
color_matrix into Frame. `Frame::wb_gains` normalizes R/B by green; it does not
expose an independent AsShotNeutral tag. Thus n above is the reciprocal of
the actual consumed as-shot WB, not a second metadata measurement.
`xyz_to_cam_rgb_with_source` selects the direct matrix if usable, otherwise
the named daylight preference. Current full caches retain selected matrix,
source label and WB bits, but not the complete illuminant table.

M85-output-correctness section2 records A and D65 matrices for ILCE-7CM2,
and a zero direct xyz_to_cam field. Actual current opal/marigold matrix-table
availability remains to be checked. The metadata route decodes exactly one
bound original from each stack, records every matrix/WB bit, and requires
camera/ISO, full geometry, levels, actual WB and selected D65 to agree with
the retained complete cache. The prototype refuses missing/duplicate A/D65,
nonfinite/singular matrices, invalid WB, a usable ambiguous direct matrix,
or an incompatible selected matrix. Never insert remembered M85 coefficients
into the photographic path. Source files are hashed and checked unchanged.

Source-only cache read confirms the selected inputs: opal-headroom/cache-1
baseline and garnet-spatial-trace/marigold4-fixed-1 candidate (the latter is
the corrected Current image). Both record WB bits
`[1071144960,1065353216,1075924992]`, the same D65 bits, and the same levels.
They contain 155/ref77 and 488/ref244 sources respectively. These saved facts
support the held WB comparison; they still do not supply either current A
matrix. CIE's [standard-illuminant definition](https://www.cie.co.at/eilv/168)
states approximately 2856 K for A and 6500 K for D65; the fixed 6504 K endpoint
above is the declared conventional rounded coordinate, not a fresh CCT fit.

## Consumer and decisions

Use unchanged cached native CFA planes, same WB/MHC, exposure, resolved tone,
sensor ceilings, sensor rolloff, gamut map, ICC and dimensions. First render
Current and require complete RGB16/ICC equality with the bound current master.
Then reproduce it with the exact pinned writer; complete RGB16/ICC must match.
Replace only the matrix and verify every other resolved-development field
remains bit-identical. Record both matrices, complete image/cache hashes and
all metadata. No RAW read is allowed in the cached phase.

Holding those downstream stages means their code and settings are unchanged,
not identical per-pixel behavior. Sensor pin decisions and rolloff weight use
the held camera values/ceilings, but the rolloff neutral luminance depends on
the replacement matrix. Tone gain sees the changed post-matrix luminance, and
gamut decisions can change. The pair measures the complete developer's response
to this one matrix replacement; it does not isolate a linear transform after
disabling or bypassing those stages.

Independent controls must challenge non-neutral vectors, inversion/transpose,
Y normalization, inverse-WB placement, endpoint/interior interpolation and
malformed calibration. Appended-CAT and omitted-inverse-WB mutants must fail.
Two distinct matrices can preserve neutral; that property alone does not
qualify color fidelity. Flat/noise and true colored/bright edges must remain
reported. Root executes the exact frozen controls and two metadata captures
before cached image arms. No general CCT solver, parameter sweep or profile
fitting is included.

Show complete opal and marigold before/after images and masters, then inspect
the existing frozen native colored/bright targets. A useful visible color
separation must preserve genuine facets/petals and avoid stronger false
fringes. Increased saturation or fewer white pixels alone cannot pass. There
is no physical color reference here, so the result cannot establish absolute
color accuracy, glare recovery or removal of spatial ghosting.

New CLI sibling: `illuminant_aware_color`, including implementation.rs;
public child `operator` includes operator.rs, and `independent_controls`
includes independent-controls.rs. No new image_out hook is needed. Ignored
routes are `metadata_pair` and `cached_pair`, config environment
`STREHL_ILLUMINANT_AWARE_COLOR_CONFIG`. Root's runner owns resource bounds,
source bindings, generated-control completion and whole/native views.
