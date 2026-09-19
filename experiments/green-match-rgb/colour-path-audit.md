# Warm manual-WB colour path: unvalidated accuracy, no duplicate WB found

**READ-ONLY VERDICT:** the current path is internally consistent with its stated
camera-space white-balance approximation. I found no duplicate WB or accidental
second pixel white-point adaptation in the inspected consumer/developer. Its
colour accuracy for this 3000 K capture has **not** been established. The saved
Sony preview itself is visibly blue/cyan, so blue appearance alone cannot locate
a Strehl defect. No settings, images or rendering code were changed.

Search: `prior_art.py white-balance matrix adaptation illuminant`, then targeted
safe project source/reports. The decisive prior result is M85 sections2/3/8:
matrix orientation and arithmetic were checked, but colour accuracy was
explicitly unclaimed. `color.rs:166` likewise states that dual-illuminant
interpolation and explicit chromatic adaptation are absent, with residual error
under strongly non-daylight illumination untested. No warm-manual-WB validation
was located. The daylight-WB plausibility test at `color.rs:1173` is a matrix
orientation check, not a test of the current warm capture.

## Actual handling

- Saved capture metadata reports manual colour-temperature/filter WB at 3000 K
  for DSC00094/00129/00163. The actual baseline log records as-shot gains
  `[1.5986, 1, 2.7090]`, and the exporter receipt holds the same exact WB bits
  across all 70 frames. Matrix source is `decoder color_matrix[D65]`.
- `Frame::xyz_to_cam_rgb_with_source` always prefers daylight matrices; it does
  not choose/interpolate from shot WB. `camera_to_srgb` forms
  `inverse(row_normalize(M_D65 * sRGB_to_XYZ_D65))`. Together with the separate
  as-shot gains this is camera-space diagonal adaptation, not two WB operations.
  Neutral camera RGB after WB remains neutral; off-neutral colour can change.
- The direct gather applies WB for MHC and divides those gains out on return to
  native-DN planes (`align_cmd.rs:2362`, GPU integration's `inverse_gain`). The
  final camera-RGB conversion applies WB once. `develop_pixel` then calls the
  colour transform, highlight handling, held tone and sRGB encoding; the WB
  passed to `with_saturation` defines clipping ceilings, not another gain.
- `image_out.rs:285` adapts **ICC profile primaries** from D65 to the required
  D50 profile-connection space. It does not apply that Bradford matrix to image
  pixels. Existing profile white/transfer tests cover this distinction.

The D65 choice is a documented approximation whose original daylight-corpus
premise no longer covers this capture. The sRGB target being D65 does not by
itself validate a D65 camera characterization under 3000 K. Equally, substituting
the A matrix alone would not establish the correct adaptation. This audit does
not identify the approximation as the cause or magnitude of any excess blue.

## One existing-file falsifier

**Already inspected:** the camera-rendered
`quality-september19/new-captures-1/crystalized-vitamin-c-cpl-035-embedded.jpg`
(DSC00129, SHA256 `9de88cd818d84eb2df4fea1a8292f196dec5312dad82d1341bce750bfe94fc47`)
has pale blue/cyan across both background and crystals. This rejects the strong
hypothesis that Strehl introduced *all* of the visible blue. It is visual
evidence from an independent developer, not a physical colour reference.

**Exact next check, not run:** compare that saved preview with the already
developed **same source** `vitamin-c-comparator-2/developed/DSC00129.tiff`, not
the focus merge. Freeze two broad corresponding rectangles in the preview,
`[80,700,240,860]` and `[1280,160,1440,320]` (half-open xyxy), confirm their
landmark correspondence in the full source, and report each image's RGB channel
ordering and normalized mean RGB. Do not fit gains or declare either rectangle
neutral. A camera-neutral/warm versus Strehl-blue disagreement would falsify
matching broad colour appearance and justify a controlled developer audit;
agreement would close the claim of a Strehl-only global cast, not validate
3000 K colourimetry. A channel-swapped copy is the comparison's cheap destroyer.
Different Sony tone/gamut processing, JPEG quantization and possible preview
framing remain limits; this check cannot assign a discrepancy to the matrix
alone. No RAW decode, rerender or new capture is needed.
