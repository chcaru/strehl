# Product17 repeat-proposal photographic review

Independent reviewer; complete-scene and frozen native-witness review. This review does not authorize default promotion or infer temporal noise from image differences.

## Bound experiment and verification

The frozen driver is completion/review/repeat-proposal-full.py; the separate repeat-proposal-full-readback.py preserves that already-running source. Artifacts are outputs/multi-stack/overflow/repeat-proposals-17. The three commands reuse the actual product16 equal-run command, changing the executable/output directory and adding only the respective grouping control:

| Arm | Additional flag | Groups | Cross-pass pairs |
| --- | --- | ---: | ---: |
| legacy | none | 28 | 4 |
| proposals | --uncertainty-repeat-proposals | 16 | 16 |
| singletons | --no-repeat-grouping | 32 | 0 |

Every arm retains all32 original identities exactly once. Common settings are eight workers,16GiB budget, Catmull-Rom, seven pyramid bands, gate2, exponent2, sharpen1.4, exposure0, agreement4, focus evidence and contribution maps. Primary and precision weighting are off. All use the same saved joint map and isolated STREHL_WARPMAP. No sensor-CFA master was exported by this product17 simple-session path; the available linear master is RGB.

VERIFIED independently from each run receipt: complete/exit0, executable SHA256 036042897ce3bf4034f8c97db9859ebdb1b7b175aac7f246ba1602e54f86355f, and environment exactly match the frozen plan. Elapsed times66.887/64.659/67.664 seconds and sampled private peaks8,416,104,448/8,440,823,808/8,416,088,064 bytes are provenance, not a controlled performance comparison.

VERIFIED by source review and retained complete-readback.json: completed.json binds render-completion.json, which binds all required output/session files; each arm has exactly matching source-identities, alignment, calibration and session hashes. Both complete TIFFs have shape4668x7004x3; master is finite float32 and photograph is uint16. Legacy photograph and master pixel bits are identical to product16 across the complete image. The reviewer inspected the verifier and receipts rather than rerunning another whole-image numerical scan. Readback-plan SHA256470fe4a06307914ac4bf48caf414c75bc5dea62b77d3e851179801e1c93ad7b4 freezes the baseline references before new-image inspection.

## Display and inspected coverage

The original frozen transform is unchanged: linear RGB black0.00033, white0.38858, then sRGB transfer and8-bit display. No candidate-derived exposure, contrast, registration or ROI fitting was performed. I viewed each complete7004x4668 fixed-display PNG; the viewer resized these to1920x1280, so they establish scene-wide orientation and conspicuous artifacts, not native detail. I separately viewed all27 native384x384 witness PNGs, with no resize notices, and rechecked all18 corresponding existing passA/passB witnesses. The pass controls are appearance references, not independent truth.

| Frozen witness | Output origin, sensor pixels | Inspection finding |
| --- | --- | --- |
| dark-background | 841,2404 | Near black; isolated colored points remain. Original display has low sensitivity to fine shadow variation. |
| upper-background | 5447,318 | Near black; same limitation, no reliable noise conclusion. |
| antenna-shaft | 2318,2531 | Same blurred shaft edges, circular reflections and crossing hairs. Tonal/grain changes are subtle. |
| eye-facets | 3710,2292 | Facet rows and existing color modulation persist. No new recognizable detail or obvious structural loss. |
| dark-eye | 3598,2568 | Dark facet pattern retained; small tonal differences, limited shadow visibility. |
| brow-hairs | 3577,1752 | Bright hairs, thin dark crossing strand and existing edge fringing remain. No clear detail advantage. |
| chin-hairs | 3535,3098 | Hair edges and highlights remain coherent; existing green/magenta fringes persist in both single-pass controls too. |
| defocused-body | 1966,3487 | Broader grouping appears subtly smoother in the soft tonal field; this is appearance, not measured temporal variance. |
| specular-face | 4231,1795 | Broad reflections and existing colored edges retained; no new conspicuous seam or blotch. |

All dimensions are384x384. Full-sensor origins add[14,10] to the listed output origins. The frozen readback verifies these exact origins against the original inspection receipt. Image hashes are retained in each inspection/arm/receipt.json.

## Bounded photographic conclusion

OBSERVED: all three complete scenes preserve the same composition and broad appearance. I found no new seam, gross color break or obvious hair/facet erasure in the whole-scene views and all frozen native witnesses. Broader grouping looks slightly smoother in some soft tonal regions, but the change is small under the original display. I cannot establish a useful scene-wide noise/detail improvement from these views, and this is not a statistical finding of zero SNR improvement.

The near-black witnesses justify a separately frozen, baseline-derived common shadow display to inspect visible chromatic patterns. Such a diagnostic must retain the original nine-witness review and label any narrower shadow-only subset; it cannot turn spatial texture or fixed-pattern changes into a temporal-noise estimate.

No primary was selected in these three arms. Agreement with passA/passB appearance therefore cannot certify optional-primary preservation. The actual-core PSF controls remain relevant contrary evidence: grouping can attenuate clean signal even when noisy reference MSE improves, and primary is a disagreement fallback rather than an unconditional appearance constraint. The oracle precision result addresses unequal-noise weighting under exact predictions, not real-guide calibration or those PSF differences.

The positive independent-reference two-acquisition assay remains a separate conditional operator result. Its reference acquisitions are included in these full32 outputs, so direct comparison to them would reuse reference photons and cannot establish independent full32 risk. A predeclared24-source full-consumer comparison excluding all eight reference acquisitions could test that bridge, with each physical reference state retained and shared all32-derived geometry explicitly conditional. An original-CFA incremental-noise control can characterize sensitivity of the exact32-source consumer but would remain a simulated-noise-on-real-signal result. Neither should be relabelled pure camera noise or unbiased full32 SNR.

## Separate fixed shadow-display appendix

After completing the unchanged-display review, I inspected all10 native384 images in shadow-inspection: the same two preexisting background witnesses for legacy, proposals, singletons, passA and passB. The common transform was frozen solely from pooled baseline background values: black0.00016193918658245822 and white0.0014710793475387666, the baseline0.1/99.9 percentiles, followed by the same sRGB transfer. No candidate values chose the transform or locations. Plan SHA2569ecdce2ccd1689b77410fff6f490c66c889c136940c1daa2707d981696be9f79 and the receipt retain display/crop hashes and clipped fractions for every arm.

OBSERVED positive: broader proposals have visibly less fine chromatic granularity in both background witnesses than legacy, all-single and either passA/passB. I did not find a new conspicuous large-scale chromatic blotch pattern. Isolated points and some residual texture remain. This difference is clear under the strong common shadow lift, whereas it was largely invisible under the normal frozen display.

Combined with the complete-scene and all27 native-witness review above, this is evidence of a bounded appearance benefit in the strongly lifted shadows of this actual complete photograph, without an observed conspicuous subject-structure regression in the tested witnesses. It is not a temporal sigma measurement, pure sensor-noise reduction, resolved-detail gain or blanket justification to broaden focus groups on other captures. The synthetic PSF/unequal-noise counterexamples and optional-primary limitations remain operative.
