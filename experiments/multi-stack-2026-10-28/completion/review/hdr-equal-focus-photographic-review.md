# HDR equal-observation precision photographic review

VERIFIED visual observations, 2026-10-28, root/independent_review. The complete 6928 x 4620 precision03 float master was read with finite-value checks and inspected as a complete composition plus all twelve previously frozen native 384 witnesses. Equal HDR, precision01, precision03, short2.5s and long6s were compared in twelve paste-only boards: sixty native crops, no crop resampling. This reviewer authored earlier core precision/attribution fixes but did not author the equal-observation focus change, its causal experiment, guide selection or the CLI HDR orchestration. This is an independent outcome-observer challenge, not wholly author-independent validation of every precision component.

## Outcome

The new equal-observation focus variant preserves a coherent complete photograph and the earlier HDR result's avoidance of the long-only blur and bright-dot halos. No new large seam, duplicated structure, missing area or broad color break is visible. Precision03 remains closely similar to equal HDR and precision01. These witnesses do not establish an additional visible detail or noise benefit over equal HDR or the short-only control. Several sharp bar and QR boundaries remain mildly softer than short-only. The core causal experiment's measured conditional noise reduction is useful evidence with its own scope; it is not converted here into an unmeasured photographic sigma claim.

| Frozen witness | Five-arm observation |
| --- | --- |
| qr-white-black-grid | Same grid structure and persistent edge softness; no recognizable extra structure in precision03 |
| qr-corner-boundary | All fused arms preserve the corner much better than long-only; short-only retains a slightly crisper boundary |
| fine-resolution-bars | Bar separation retained in fused arms; long-only strongly blurred; precision03 adds no newly separated bars |
| bright-dot-field | Fused arms retain dot boundaries without the long-only plateaus/halos; no additional precision03 improvement established |
| low-contrast-dot-field | Closely similar dots and marks; spatial texture is not a temporal-noise observer |
| lower-radial-spokes | Same resolved outer spokes, central merging and color fringes; no added precision03 resolution |
| large-radial-star | Same radial junction and marks, with long-only broader; no clear new detail |
| gray-ramp-middle | Small marks retained; no visual noise measurement or additional precision gain claimed |
| adverse-flare-p12 | Retains the earlier boundary and flare behavior; does not demonstrate focus-independent radiometry |
| clipped-core | Nearly flat fused/short field; uniformity alone does not prove recovered detail |
| blue-clipped-core | Same limitation as clipped-core; retained source clipping/support evidence remains necessary |
| clipped-boundary | Same broad transition and texture; no new detail claim |

## Bound comparison

[prepare-hdr-focus-reference.py](prepare-hdr-focus-reference.py) verified exact serialized warpmap equality, canvas [26,17,3464,2310], identical ordered source-path/gain pairs, and development reference pass1 across equal HDR, precision01 and precision03. Precision03 explicitly records `precision_focus_reference: equal-observation`. The previously frozen physical display remains black0, white4, contrast0.55, exposure gain1; all twelve previously frozen native crop origins were reused without adjustment. No image fitting, new witness selection, auto-leveling or cross-gauge metric was used.

The complete display and crop binding are retained under `outputs/multi-stack/completion/independent-photographs/hdr-precision03`. `comparison-binding.json` binds the three render reports and recipe. `native-comparisons/layout.json` binds every source PNG and output board and records paste origins; source-to-pasted pixels were asserted identical. Native board dimensions1184 x 820 contain five 384 x 384 images, with only labels/margins added. Complete-scene overviews are orientation only.

The original clipping and uncensored-support qualifications in [the earlier HDR review](../../review/hdr-photographic-review.md) still apply. A display-white or gray pixel is not a clipping test. In particular, the two core witnesses lack recognizable local detail and cannot support a recovered-detail claim.

## Relationship to the causal noise result

The [conditional observer audit](conditional-noise-observer-audit.md) independently checked the actual-core equal-observation arm: approximately 11.6% lower conditional injected-noise variance, approximately 6% lower sigma, with its clean result agreeing with equal weighting to floating-point roundoff in that fixture. That evidence conditions on the frozen guide and planted signal/geometry and does not calibrate camera noise, registration uncertainty or real photographic temporal variance. The present complete-output inspection supplies a bounded preservation check; it neither negates that conditional result nor supplies the missing real-photon noise proof.

Command actually run for saved-output preparation:

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/prepare-hdr-focus-reference.py
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/compose-hdr-focus-reference.py
```

The native-board preparation read existing PNGs through Pillow, pasted each without scaling, asserted exact pasted bytes, and wrote SHA256 layout receipts. All twelve boards and the complete precision03 composition were then visually inspected using `view_image` with original detail. No RAW decoding or renderer was run by this reviewer.
