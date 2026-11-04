# Appearance Layers13: independent full photograph review

**VERIFIED useful retained appearance choice.** The full b17/b18 pair produces two coherent 6520×4344 photographs in the same saved crop. The second capture preserves strong localized green reflections across the dorsal ridges; the first preserves a quieter blue/dark appearance. The eye facets, major grooves and body features remain recognizable in both. Keeping these as separate Layers gives a concrete choice that averaging would dilute.

This is an appearance-layer result. The acquisition does not supply calibrated CPL angles, light directions or reflectance standards. It therefore does not identify a diffuse/specular decomposition, surface normals, optical resolution or a general color-fidelity winner. Both retained calibrations use exactly the same WB [1.5986328125,1,2.708984375], ISO 100 and sensor levels. Shutter differs 5 s versus 3.2 s; those exposures and any lighting/polarizer movement remain part of the comparison.

## Complete artifact and display evidence

The run used all 299 originals from each capture, 598 total, with frozen CLI13 SHA 4e8934a6447a2cf68d02e59bc1db918dfb6e60fe9283a4e05f59709228ec6d3d. Native alignment placed 598/598, with 4421 fits and 3824 anchor-component cycles. Shared full geometry 3516×2344 quad, reference 149; both delivered photographs are 6520×4344 native pixels. Each report contains only its own pass's 299 frames, all photometric gains 1, no cross-pass grouping, and the same saved merge recipe.

The complete decoded float masters are finite and equal mapped pixels bit-for-bit. Both renderer output bindings and parent completion verify. Full artifact identities and exact recipe are retained in outputs/multi-stack/completion/appearance-review-13/artifact-audit.json. Actual run receipt is outputs/multi-stack/completion/appearance-layers-run-13/receipt.json: exit 0, 2240.841 s, 8 workers, 16 GiB limit, sampled peak private 13,404,991,488 bytes. This shared-host capability run is not an isolated performance measurement.

Display parameters and integer native origins were frozen from first-layer metadata and the predeclared UV protocol before second-layer pixels were opened. Independent display math exactly reproduced every 16-bit encoded first-layer photo channel. Both complete images were opened in view_image at 1921×1280 orientation scale. All eight native paired boards were inspected without spatial resampling: each panel is an exact 384×384 slice. This is complete-photo plus native-witness evidence, not a resized crop quality claim.

Commands actually run:

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/review-diversity-layers.py prepare --run outputs/multi-stack/completion/appearance-layers-13 --out outputs/multi-stack/completion/appearance-review-13 --key appearance
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/review-diversity-layers.py finish --run outputs/multi-stack/completion/appearance-layers-13 --out outputs/multi-stack/completion/appearance-review-13
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/appearance-selection-controls.py
```

## Fixed native witnesses and adverse controls

| Witness | Observation |
| --- | --- |
| green-left | Clear green localized reflections in layer 02 where layer 01 is blue/dark. This is the strongest useful appearance choice. |
| green-center | Central tan structure remains coherent; layer 02 has a strong green reflection beside its lower edge. Layer01's tan highlight is brighter. |
| neutral-ridge | Same major boundary and rounded features; localized green differences persist below it. Soft/colored edge structure is present in both and is not claimed fixed. |
| brown-eye | Facet texture and purple reflection remain recognizable and similarly placed. No extra resolved-detail claim. |
| eye-lower-rim | Similar rounded structures and dark troughs; bright colored highlights persist in both. |
| dark-left-groove | Long dark groove and bright ridge boundaries remain coherent; no obvious new double edge from layer preservation. |
| lower-body | Similar sparse bright structures and dark field. This is not a noise metric. |
| background | The frozen center actually lands on the lower body/edge after cropping. It was not reselected and is not used as a flat background/noise witness. |

The predeclared nominal shutter-only control multiplies the first linear master by 3.2/5. It dims the first appearance without creating the second's localized green reflections. The null control reproduces all eight frozen first-layer crops exactly. An equal post-render RGB mean reduces the distinctive green appearance; this is an illustration of the choice being preserved, not an actual RAW-fusion foil or a quality score. The 8 px perpendicular eye-shift control visibly softens/doubles facet and boundary structure. All these native controls are retained with receipts; no image fitting or local enhancement was used.

Whole-scene views show scattered colored bright points in dark surrounding areas, and native specular regions retain some soft/colored halos. These are limitations of the delivered photographs. Without matched independent ordinary baselines, this review cannot attribute those effects to the session alignment or claim ordinary nonregression on these new captures. The Layers mechanism itself does not synthesize the second appearance from the first.

## Completion status

L1 now has a complete real pair demonstrating useful appearance preservation and a concrete choice of reflection rendering. The next product snapshot must still exercise actual desktop layer selection, persistent reopen and selected-photo export on these files. Calibrated physical polarimetric separation remains outside the evidence. V1 remains separate: the underside/top IndependentViews14 run is now active, with its own frozen protocol and no forced cross-view warp.

## Product15 workflow update

Actual GPU import, both output selections, separate-process persisted reopen and native-size PNG exports passed. All corresponding overlay and clean photograph screenshots were visually inspected; see [the product workflow review](ui15-diversity-workflow-review.md). The earlier pending desktop requirement is satisfied for this Layers pair. This adds usable selection/export evidence, without expanding the physical photographic claims above.
