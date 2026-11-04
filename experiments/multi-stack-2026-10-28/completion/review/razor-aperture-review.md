# Razor aperture Layers13: independent complete-output review

**VERIFIED useful aperture selection; not an optical-resolution or fused-detail claim.** Both complete 6912×4608 photographs and linear masters were inspected under the same first-layer display transform, together with eight frozen 384×384 native witnesses. For this razor capture, the f/8 layer is the useful choice for compact dust/specular features and darker lettering. The f/5.6 layer has conspicuous larger bright blobs and pale surrounds around those features. The product preserves both aligned appearances instead of averaging this difference away.

The f/8 photograph is also darker: both captures used 3.2s but different apertures. That is a major confound for a sharpness/noise conclusion. A secondary, explicitly post-inspection sanity control raised f/8 by the nominal aperture-area ratio(8/5.6)^2 and dimmed f/5.6 by its inverse, without image fitting. The compact dust structures remain in the raised f/8 witness while the dimmed f/5.6 witness retains broader structures. This supports a useful choice of saved layer on this scene. It does not calibrate aperture transmission, CPL position, focus coverage, diffraction, physical PSF or sensor noise.

## Identity and complete artifacts

Inputs b46/b47 are the full 67/50-file original razor sweeps. The engine placed all 117 sources with 821 native fits and 705 anchor-component cycles. Both outputs retain quad canvas [30,20,3456,2304], native 6912×4608; every reported frame belongs only to its own pass, photometric gain 1, grouping disabled, and both merge recipes are identical. The complete decoded float masters are finite and match their mapped sample bits. Bound renderer outputs and parent completion hashes verify. Detailed identities and recipe are in outputs/multi-stack/completion/razor-aperture-review-13/artifact-audit.json.

Actual run: [diversity-layers-brief.md](diversity-layers-brief.md) and outputs/multi-stack/completion/razor-aperture-layers-run-13/receipt.json. Frozen CLI13 SHA 4e8934a6447a2cf68d02e59bc1db918dfb6e60fe9283a4e05f59709228ec6d3d, 8 workers, 16 GiB limit, CatmullRom, 7 bands, gate 2, exponent 2, sharpening 1.4, exposure 0, focus evidence. Elapsed 466.087s; sampled peak private 5,997,568,000 bytes. This shared-host execution is a capability receipt, not an isolated performance comparison.

Review commands actually run from the worktree:

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/review-diversity-layers.py prepare --run outputs/multi-stack/completion/razor-aperture-layers-13 --out outputs/multi-stack/completion/razor-aperture-review-13 --key razor-aperture
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/review-diversity-layers.py finish --run outputs/multi-stack/completion/razor-aperture-layers-13 --out outputs/multi-stack/completion/razor-aperture-review-13
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/aperture-exposure-sanity.py
```

The first-layer display independently reproduced every encoded 16-bit photo channel exactly. Display parameters and native locations were frozen before second-layer pixels were opened. Both full images were opened with view_image, displayed as 1920×1280 whole-scene orientation views; they are not native-detail witnesses. Eight paired boards contain exact 384×384 panels copied without resampling. The 384 viewer commission showed resolved one-pixel stripes/checkerboard and colored boundaries. The original fixed-transform complete PNGs remain available.

## Native observations

| Frozen witness | Observation under common display |
| --- | --- |
| letter-s | f/8 preserves darker lettering and a more compact adjacent bright feature; f/5.6 has pale bloom around it. |
| letter-e | This predeclared crop landed on substrate/dust below the lettering; it was not moved. f/8 separates small bright dust features that are broad in f/5.6. |
| metal-dust | Large f/5.6 bright blobs remain broad when dimmed; raised f/8 retains smaller discrete structures. |
| metal-grooves | Horizontal grooves and texture remain continuous in both; f/8 dust is more compact. Grain contrast is not treated as detail/noise evidence. |
| edge-left | Both preserve the dark bevel and bright particles along its lower edge; common-coordinate mismatch is small but no independent subpixel registration truth is available. |
| edge-middle | Both preserve vertical bevel markings; f/5.6 is brighter. Nominally raised f/8 restores visibility without a clear additional fine-detail claim. |
| edge-right | Coherent bevel and background; no new large halo or broken seam was identified. |
| black-field | Both mostly black, with faint diagonal structure. No temporal-noise conclusion from this spatial crop. |

The zero-opacity/null rendering reproduces every frozen crop exactly. An 8 px horizontal-shift overlay is an insensitive foil for a horizontal razor edge; it was retained but not called a successful edge control. The perpendicular 8 px shift produces visibly doubled bright-edge particles and broadened horizontal boundaries. This demonstrates the viewing protocol can expose a substantial bad correspondence; it does not bound actual alignment error. No gradient-energy or aperture-ordering metric is used.

## Outcome scope

A1 now has a real useful aligned aperture comparison and a specific saved-layer selection, beyond the prior fabric export counters. Actual desktop import/selection/export of these new complete files remains due with the next product snapshot. No cross-aperture fusion or general superiority has been established. Unequal 67/50 focus spans, exposure, and possible appearance changes remain confounds for isolating aperture alone. The optical profile is reported as measured at f/5.6 and f/8, but that is not an independent calibration of this razor scene.

## Product15 workflow update

Actual GPU import, both output selections, separate-process persisted reopen and native-size PNG exports passed. All corresponding overlay and clean photograph screenshots were visually inspected; see [the product workflow review](ui15-diversity-workflow-review.md). The earlier pending desktop requirement is satisfied for this Layers pair. This adds usable selection/export evidence, without expanding the physical photographic claims above.
