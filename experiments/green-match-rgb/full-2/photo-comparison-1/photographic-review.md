# Independent photographic review: modest cleanup, fans unresolved

**VISUAL DECISION:** this complete comparison shows a useful but modest
cleanup of fine grain in smooth regions. It does not show a convincing repair
of the long coloured fans, nor establish additional resolved detail. Keep the
mode experimental; this single stack does not support default promotion or a
SOTA claim.

I inspected both complete 1560-pixel overview images and all five frozen
384x384 native pairs individually, before reading any root visual verdict.
The overview is for whole-field orientation only. Native observations use the
unresampled PNGs, identically converted from the RGB16 masters. The coordinate
receipt confirms unchanged crop (28,19,3460,2306) quads, zero translation of
the frozen windows and complete extent 6920x4612. Completion records exact
baseline pixel identity with the held baseline; TIFF whole-file hashes differ.

| Fixed window | Independent observation |
| --- | --- |
| facet-edges | The conspicuous glint and its long coloured rays remain. Fine grain in nearby smooth areas is reduced, but no convincing shortening or removal of the fan is visible. Major facet contours remain recognizable. |
| dark-inclusion | The lower-left bright coloured fan persists with broadly the same shape and extent. Surrounding texture looks smoother; the black inclusion and larger boundaries remain. This is not an established repair of the extended source feature. |
| pale-background | The clearest improvement: less fine grain across the smooth blue field. Broad shading and the visible dust-like spots/marks persist. This is a visual texture observation, not a calibrated temporal-noise measurement. |
| bright-facet | Fine grain is reduced across the largely soft background. The fragment edge near the top remains. This window is mostly soft content, so it cannot establish preservation of highly resolved fine detail merely from its name. |
| fine-crystals | Major sloping crystal boundaries and identifiable features remain, with less fine roughness. Subtler texture also appears smoother. The comparison does not separate removal of noise/manufactured contrast from some fine-detail attenuation, and coloured glint fringes remain. |

The complete overviews look very similar in overall tone, cool colour and
large-scale geometry. I see no large hue shift or obvious new seam in the
fixed native views. That limited observation does not prove true-colour
accuracy or preservation of every fine feature. The target fan defect remains
more conspicuous than the incremental cleanup.

**MEASURED participation, not a quality score:** I read only the saved
`acceptance-counts.u8` map for the same five coordinate-receipt windows. Each
contains 36864 quads. The counts are:

| Window | Median accepted sources | Zero-source fallback quads | One-source quads |
| --- | ---: | ---: | ---: |
| facet-edges | 10 | 1292 | 1864 |
| pale-background | 23 | 2 | 135 |
| fine-crystals | 10 | 719 | 1296 |
| bright-facet | 21 | 9 | 142 |
| dark-inclusion | 11 | 946 | 1145 |

Across the complete 7978760-quad output, 75414 quads use unchanged-baseline
fallback and the mean accepted count is 16.86. The full-stack intervention is
therefore active and often averages many sources; the lack of fan improvement
cannot be described as the entire result reverting to baseline. These regional
counts do not identify the exact sources contributing to a particular ray and
do not establish that all accepted observations have compatible colour/depth.
The higher acceptance in smooth regions is consistent with the visible cleanup,
but is not itself evidence of image quality.

Provenance: `coordinate-receipt.json`, `../output/receipt.json` and
`../completion.json`. Baseline TIFF SHA256
`bc6a921000bf942e678a31d6d4374bf2d347f61e61162d1d0dc98f80212cfd9e`;
comparison TIFF SHA256
`c27d8b10fc0b702792d46b7bacbbcc57939c3255ee85b5db411d0fbcf75d8b8d`.
Root's completed pair took 94.969 s job wall time; this is a paired experiment,
not an isolated production timing benchmark. No additional regions, image
rendering, source changes, RAW reads or quality metrics were introduced by
this review.
