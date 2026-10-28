# Complete weevil CA-off comparison under one display

**VERIFIED — a bounded reduction of colored hair-edge artifacts, not a substantial
solution to the weevil's overall softness and not a general CA-profile decision.**

The complete baseline and CA-off photographs were inspected first, followed by
the dark-background control and all ten previously frozen native sites. The
most convincing change is less orange/blue separation on the upper-leg hairs.
The visible strands remain present, and the change agrees with the independently
decoded source149 and the actual consumer control. Across the complete image,
the visual change is modest. Soft scale boundaries, hard bright glints, pale
occlusion contours and faint dark-background specks remain unresolved.

No clear large regression was established in this complete-view plus ten-site
review. Some tiny glints change hue in both directions, and broad color accuracy
or a detail-resolution improvement has not been established. This is useful
causal evidence for reviewing when the fixed optical profile applies; it does
not justify disabling that profile for every capture or promoting a SOTA claim.

## Complete matched-display outputs

Both complete JPEGs contain all 6896 × 4596 output pixels. The tool displayed them
at 1920 × 1280, so these views establish composition/coverage and broad appearance,
not native detail. The RGB16 TIFF links provide the complete lossless masters.

Baseline, fixed optical-profile correction enabled:

![Complete baseline with common display](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/ca-off-review/baseline-ca-on/complete-stack.jpg)

[Full-resolution baseline common-display master](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/ca-off-review/baseline-ca-on/common-display-master.tiff)

The same complete 299-frame stack with profile correction disabled:

![Complete CA-off stack with common display](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/ca-off-review/ca-off/complete-stack.jpg)

[Full-resolution CA-off common-display master](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/ca-off-review/ca-off/common-display-master.tiff)

The original native masters remain at
[baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/weevil-107-baseline/stack-master.tiff)
and [CA-off](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff).
Their independently fitted automatic tones differ; use the common-display pair
above for this comparison. Both original float linear masters are retained and
hash-bound in `common-display-receipt.json`.

## What was held fixed

- Complete 299-source order, executable SHA256
  `89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388`, and map SHA256
  `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`.
- Delivered native RGB gauge: 6896 × 4596, reference149, native reference offset
  `(68,46)`; no crop movement, new alignment or image resampling.
- Both retained pre-tone BT.709/D65 linear masters use gain3.434, clamp0..1,
  standard sRGB transfer and round-to-RGB16. This intentionally simple display
  is common to both arms. It is not independently fitted to either image and is
  not claimed to be the original native tone curve.
- PNG/JPEG conversion is `(RGB16 + 128) // 257`; source ICC is retained. Native
  TIFF/PNG crops are exact 384 × 384 subarrays of the paired common masters.
  Only labeled full-image overviews/JPEG tool views are resized for orientation.

The original automatic tone values were baseline `[-0.00026,0.27030,0.55]` and
CA-off `[-0.00023,0.27313,0.55]`. Their difference is excluded from this verdict.
The changed experimental setting is `STREHL_FIX_CA=off`; native merge flags and
four-worker configuration remain recorded in each run's invocation.

## All frozen witnesses

All origins are in the common delivered-native gauge. Names are stable labels;
as recorded previously, `eye-and-antenna` and `elytron-seam` are not verified
anatomical identifications. Both arms of every row were viewed at native384.

| Site and origin | Observation under the common display |
| --- | --- |
| background-black `(3800,500)` | Both remain nearly black with faint colored specks. Small color differences are visible; no noise reduction is established. This is not a calibrated flat-noise measurement. |
| dark-elytron `(2750,2120)` | Weak dark texture and the pale crossing strand remain. Glint colors move slightly; no clear detail gain or large loss is established. |
| turquoise-scales `(2120,1340)` | Scale marks and gaps remain, but rounded/soft boundaries and hard cyan/white glints remain in both. The off arm does not solve the texture softness. |
| elytron-seam `(2950,1960)` | The diagonal pale strand remains continuous with similar softness. Nearby hard blue/white glints persist. No clear local improvement is established. |
| bright-wing-rim `(4050,1810)` | The broad pale curved rim and dark cavity remain, as do intense glints. Slight color changes do not remove this occlusion contour. |
| thorax-texture `(4520,2560)` | The dense pattern and dark gaps remain. A few small highlights gain or lose red/blue components; there is no general glint-color win or proven recovery of finer structure. |
| upper-leg-hairs `(1820,640)` | The strongest supported gain: orange/blue split edging on portions of the top outline and lower protruding hairs is reduced. The corresponding strands remain visible. This is a color-edge artifact reduction, not a measured increase in resolved hair detail. |
| blue-joint `(2680,850)` | Saturated blue texture, fine marks and the dark band are retained. Small hue changes are present; no broad color or focus improvement is established. |
| upper-occlusion `(3850,1300)` | The blue raised region and lower dark cavity retain their shape. The pale cyan fringe/contour remains; no demonstrated occlusion-halo fix. |
| eye-and-antenna `(5350,2920)` | The dark elongated gap, bordering texture and fine strands remain. Some edge/color separation looks less pronounced, but source support for an additional improvement was not established at this site. |

The complete output pair and ten fixed guards support a narrow this-stack
artifact-reduction finding. They do not prove that every uninspected native
location improved or that every small color change is physically more accurate.

## Causal support and practical decision

The actual production gather with CA off preserves **all four CFA phases exactly**
against original149 across the complete 31,694,016-pixel delivered rectangle.
This reviewer independently rehashed original/gathered captures and verified
their equality; their common SHA256 is
`5a488782976e13a7693b46b26084f12631cec4fbc90a28996e7069c99b13ca72`.
The previous CA-on capture changed red/blue values and visibly strengthened
colored hair-edge separation while preserving the green samples. Together these
controls isolate the profile action at anchor149, including the real gather and
rounding path. They do not assert that every non-anchor frame has identity
geometry or that disabling CA is generally correct.

**ARGUED recommendation:** retain this complete CA-off render as a useful
comparison and pursue capture-dependent profile applicability or measurement.
Do not make a global default change based on this stack. The user requested
substantial improvement of the whole insect; this bounded gain does not satisfy
that larger goal. Continue to the defects exposed by complete competitive
workflow outputs, while preserving this hair witness as a regression guard.

Executed command, exit0:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/ca-off-review/prepare-common-display.py
```

Preparation took 4.437 seconds operationally. No RAW was read, no Cargo command
was run, and no reconstruction, alignment or original render was altered.
`common-display-receipt.json` pins source/output hashes, crop coordinates,
display, actual capture and the executed producer. The full render's own
commands and runtime accounting remain in its output directory.
