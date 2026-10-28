# Complete60-source flat-slide baseline: visible defects remain

**VERIFIED visual baseline, no improvement or causal claim.** Inspected the entire unchanged photograph first, then eight frozen native384 regions. The chart is recognizable across the field, but fine bar groups are poorly separated, radial spokes merge toward their centers, and cyan/red edge separation is visible on the right bar target and lower radial target. These are useful photographic defects to test. The baseline does not establish whether capture, optical response, placement, reconstruction or development caused them.

The complete6932x4620 output is retained below. Its in-chat rendering is an overview; native judgments use the separate unresampled witnesses.

![Complete flat-slide baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/flat-1s-baseline/stack-full.jpg)

[Full-resolution RGB16 master](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/flat-1s-baseline/stack-master.tiff) · [Complete float-linear master](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/flat-1s-baseline/linear-master.tiff)

## Native observations

All crops preserve the original RGB16 pixels and ICC. Coordinates and roles were frozen from the complete composition before opening any native crop or candidate. The [manifest](frozen-witnesses.json), SHA256 `fde6bb02b6ca12793176b3e30ef8d60bba5aed3ed86dd1d4e3ea080c736a297e`, fixes their delivered native gauge; reference30 active coordinates add `(50,34)`. No region was moved after inspection.

| Frozen region | Observation |
|---|---|
| [Gray field/step](baseline-native/gray-field-step.png) | Weak vertical step remains visible amid fine mottling and faint spots. This printed/illuminated field is not certified uniform, so its spatial texture is not a sensor-noise measurement. |
| [QR block edges](baseline-native/qr-block-boundary.png) | Broad black/white shapes and corners remain recognizable. Transitions have visibly soft shoulders, with faint colored edge shading; no confident separate duplicate edge is established here. |
| [Central fine bars](baseline-native/central-fine-bars.png) | Larger horizontal and vertical groups remain separated; the nested smallest groups and numerals become indistinct. A bright thin mark crosses one upper group; its physical origin is unknown. |
| [Central micro-target](baseline-native/central-micro-target.png) | Leader lines survive continuously but look soft. Some fine bars separate while the smallest nested structures merge into gray/bright patches. No resolution number is assigned from this view. |
| [Right bar target](baseline-native/right-bar-target.png) | The same broad-to-fine loss of visible separation appears, with conspicuous cyan/red separation on several bright bars, numerals and block boundaries. A faint horizontal line traverses part of the chart; this image alone cannot label it a stacking artifact. |
| [Upper radial star](baseline-native/upper-right-star.png) | Large wedges remain distinct and converge around one visible center. Edges and the central convergence are soft; no clear extra center or double contour is identified. |
| [Lower radial center](baseline-native/bottom-radial-center.png) | Outer spokes are separated but carry colored edge rims. Toward the center, fine spokes merge into a broad pale region around the retained dark central dot. Bright isolated marks remain on some spokes. |
| [Dot field](baseline-native/dot-field.png) | Repeated circles remain recognizable but have broad soft transitions. Dark interstitial texture and isolated bright points remain; neither can be classified as noise versus real surface material from this stack alone. |

The whole view also contains broad brightness variation and many small bright marks. It is a structured calibration photograph, not an assumption of perfectly clean or uniformly illuminated truth. This review neither certifies physical resolution nor treats smoother dark fields as automatically better.

## Binding and scope

The [render receipt](../../../outputs/raw-quality-2026-10-26/flat-1s-baseline/completion.json) binds all60 sources and their unchanged bytes/metadata after the complete run, full6932x4620 crop and frozen executable. Source order is `DSC00016.ARW` through `DSC00075.ARW`; the map places60/60, reference30, crop quad `(25,17,3466,2310)`, Catmull-Rom. It contains no independent held-out placement measurement. Original preservation was checked after the full render, not between alignment and render.

Actual baseline rendering command/environment are in [invocation.json](../../../outputs/raw-quality-2026-10-26/flat-1s-baseline/invocation.json). It used normal CPU reconstruction with four workers, the matched lateral-CA profile enabled, ISO100 profile noise, levels512/15360 and as-shot WB. First/middle/last native optical headers all report ILCE-7CM2, lens identity33094,200mm,f/5.6 and coarse focus57. Those metadata values do not establish identical physical focus, shutter/IBIS state or capture-era lighting. No weevil CA-off setting was transferred.

The independently bound linear master is single-page float32, shape `(4620,6932,3)`,384314146bytes, SHA256 `51fd1f3e281c10def359af38a2064055de11b8788ff5ce7c0428d9e5a9e417ab`. Its exact product DisplayBaseline is black0.008842854, white0.36849296, contrast0.55, exposure_gain1.0. No new display transform was fitted. A future comparison must reuse this display or prospectively declare one common transform for the complete pair.

Authorized crop command actually run:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-baseline/export-frozen-crops.py
```

Exit0;0.921s recorded by the helper. [Crop export receipt](crop-export-receipt.json) verifies exact TIFF subarrays, PNG conversion `(value+128)//257`, ICC preservation, full input hashes before/after and zero RAW reads. The baseline's67.1s render log and crop time are operational observations during the concurrent weevil run, not a competitive speed comparison. No candidate was rendered, viewed or admitted by this review.
