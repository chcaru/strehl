# Highlight support: bounded source and prior audit

**Decision — ARGUED:** a distinct question remains: can RAW reconstruction distinguish original saturation from values created by signed interpolation, and preserve real highlight structure while using that provenance? The present counts do not justify a clipping threshold, smoothing, a new white level, or a photographic improvement claim. Green-phase work remains primary; this audit starts no new execution lane.

## What the retained output establishes

**VERIFIED from existing metadata, not remeasured pixels.** The [exact sensor sidecar](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/sensor-master.tiff.json) records G1 maximum31285.830078125 with384 above-white sites; G2 maximum26614.24609375 with449; B maximum16244.05859375 with17; R maximum10443.1806640625 with0. The [render log](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/render.log) uses black512/white15360, hence working white14848 above black. The sidecar is signed black-subtracted camera DN, before WB, normalization, final demosaic, matrix, tone and restoration. It records InputRange, full-resolution gather, CA off, defects off, no photometric correction, no region recipe, and no direct-plane/GPU-gather feature. It is not display clipping or a reversed color matrix.

The [earlier original decode checks](../photo-review/source-check.md) found exact RAW sample agreement on the shared active rectangle but different exposed white metadata: RawPy16383 versus product15360. That distinction matters near saturation; it does not explain green values above26000 or31000. This audit does not independently calibrate the camera's physical saturation point, inspect the remaining original frames, or locate the over-white sites.

## Actual source path

**VERIFIED source; DERIVED implication.** `align_cmd.rs::warp_frame_in_place_fullres_outputs` black-subtracts and applies source WB, performs MHC, gathers each reconstructed color channel, then removes its WB. `writeback_fullres_site` rounds and clamps only to the u16 container0..65535, not the declared source white or14-bit maximum. MHC has signed correction taps, and the retained map explicitly records ordinary `catmull-rom`, also a signed interpolation. Green's gain1 does not remove the R/B correction information already entering reconstructed green at missing green sites. This audit does not assign an individual peak to MHC versus gather.

`pyramid.rs` records its input hull from the **supplied gathered planes**, before decomposition, and clamps the final collapsed result to that per-site range. The CLI gives `sensor_master::finish` those planes and `levels.white-levels.black`; the observer counts above-white values without changing them. Thus InputRange permits interpolation-created high values. Subject to the recorded unrepaired finite path, a final31285-DN value requires an aligned input bound at least that high at that phase/site. It is not evidence that the pyramid alone invented a value outside its input hull. Nor is being inside that hull proof of faithful image reconstruction.

Relevant source locations: [gather and writeback](../../../crates/strehl-cli/src/align_cmd.rs), [input bound and collapse](../../../crates/strehl-core/src/pyramid.rs), [sensor observer](../../../crates/strehl-cli/src/merge_cmd/sensor-master.rs). No pixel execution or new arithmetic experiment was performed.

## Prior decisions that constrain the question

| Prior | Consequence |
|---|---|
| [BUILD-HULL](../../../docs/research/BUILD-HULL.md) | Its historical identity-alignment convexity result did not explain a real occlusion artifact; an in-hull result can still be wrong. It already identifies signed MHC/gather behavior. |
| [M26](../../../docs/research/M26-colour-clipping-measured.md) and [BUILD-HIGHLIGHT](../../../docs/research/BUILD-HIGHLIGHT.md) | Original saturation can manufacture strong focus evidence; raw usable white, original container and output ceilings differ. A rendered maximum is not automatically a ceiling. M26's proposed mask is historical, author-only evidence, not authorization for blanket rejection here. Existing highlight roll-off addresses development color, not spatial detail recovery. |
| [Garnet trace design](../../garnet-spatial-trace/design.md) | Already warns that gathered u16 may exceed original14-bit codes. Its separate numerator-overflow mechanism cannot be inferred from these finite maxima. |
| [Fine-support rejection](../../fine-support-guidance/candidate-independent-results.md) | Radius32 pooling reduced noise/chroma while destroying roughly58–59% of real glint-core recovery. Cleaner-looking highlights are insufficient. |
| [CA-before-MHC photographic review](../../ca-before-mhc/photographic-review.md) | Generated color gains did not yield meaningful full-chip photographic improvement. Reordering or smaller chroma error alone is insufficient. |

## Distinct remaining question, not a proposed fix

**UNVERIFIED:** whether original censoring, cross-channel MHC support or resampling overshoot materially changes focus evidence and retained highlight shape on this weevil. Original saturation is a censored observation; an interpolated over-white number is a different kind of evidence. Neither is a reliable signal to select a darker or more defocused frame. True unsaturated specular structure must survive, including its peak, color and adjacent low-contrast detail at other depths.

If root later prioritizes this, the useful first discriminator is a bounded observation through the actual source/gather/merge support at an independently identified visible defect, separating original codes, signed reconstruction and final bound. It must include an unsaturated sharp glint and a depth-boundary control. No source threshold or new smoothing recipe follows until that establishes a photographic mechanism. Complete fixed-display outputs and full masters remain mandatory for any eventual quality claim. No new RAW reads, source-pixel reads, builds, fits or numerical jobs were run for this audit.
