# Weevil 107 baseline: frozen photographic witnesses

**VERIFIED — baseline inspection only. No photographic improvement or SOTA result is claimed.**

The complete 299-frame output was inspected before selecting native witnesses.
The `view_image` response reduced the complete 6896 × 4596 JPEG to 1920 × 1280;
that view establishes composition and coverage only. Ten fixed 384 × 384 sites
were then exported from the RGB16 master and inspected individually with
`detail: original`. No candidate photograph had been seen when the coordinates
were frozen, and no candidate photograph was inspected in this review.

![Complete baseline, orientation only](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/stack-full.jpg)

[Complete RGB16 master](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/stack-master.tiff)
and [linear master](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/linear-master.tiff).
The complete photograph remains the decision surface; these native sites are
fixed regression witnesses, not a substitute for full-output comparison.

## Binding and display

- Input: `D:/personal/macro/insects/bug-3/107MSDCF`, all 299 frames, ordered as in
  the baseline [input manifest](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json).
- RGB16 master SHA256:
  `ecfae13e937f44445f3fe2a83a2e72861c4cd6cd9f56f02139f3f5e3dc0f9665`.
- Runtime placement map SHA256:
  `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`.
- All coordinates below are in delivered native RGB pixels, origin at the
  cropped master top-left. The crop is quad `(34,23,3448,2298)`, or native
  reference offset `(68,46)`. The reference is frame 149. They are not original
  per-frame sensor coordinates.
- [Frozen manifest](baseline-witnesses.json) binds each TIFF/PNG and its pixels.
  TIFF crops contain exact RGB16 subarrays. PNGs use only
  `(value + 128) // 257` conversion to RGB8. Neither format is resized; both
  retain the master's ICC. No local exposure, contrast, sharpening, or denoising
  was applied. Export round trips were exact.
- The 384 × 384 [commissioning pattern](viewer-commission-384.png) was inspected
  with `detail: original`. Vertical and horizontal one-pixel stripe directions,
  fine diagonal pattern and checker pattern were distinguishable. This confirms
  a useful native inspection path, not independently calibrated screen color.
- These are observations of the existing as-shot WB and developed baseline.
  Absolute color accuracy, clipping in sensor space, focus adequacy and which
  structures have source support remain **UNVERIFIED** without source witnesses.

The render's executed command, resolved flags, environment, executable binding
and process accounting are in its [invocation](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/invocation.json)
and [render receipt](../../../outputs/raw-quality-2026-10-26/weevil-107-baseline/render-process.json).
This review did not rebuild, realign or rerender. It decoded zero original RAWs.

## Native observations

**VERIFIED** below means visually present in the frozen baseline PNG. It does
not establish that the stacker introduced it. Names were selected from the
overview and are stable identifiers, not verified anatomical classifications.

| Witness | Native origin | Baseline observation and useful discriminator |
| --- | --- | --- |
| [background-black](baseline-native/background-black.png) | 3800,500 | Nearly black with sparse extremely faint color specks. It can reveal new texture, ringing or raised blacks, but is too dark to certify a noise-flat or prove denoising quality. |
| [dark-elytron](baseline-native/dark-elytron.png) | 2750,2120 | Dense dim material texture is visible between scale patches. A thin pale diagonal strand/line crosses the upper area. Bright glints contain small hard white centers. Preserve the weak texture and line continuity; a smoother dark area alone is no success. |
| [turquoise-scales](baseline-native/turquoise-scales.png) | 2120,1340 | Many scale boundaries are rounded/soft and adjacent cyan/green marks merge. Black gaps and isolated glints remain distinct; some glints have hard white centers and blue/cyan rims. Better local contrast alone could falsely look sharper here. |
| [elytron-seam](baseline-native/elytron-seam.png) | 2950,1960 | A pale diagonal strand/line crosses dark and scale-covered areas, with local changes in width/brightness and colored edging. It is not a verified anatomical seam. Nearby scales are soft and bright glints are harder than their surroundings. Preserve the full line and adjacent dark texture. |
| [bright-wing-rim](baseline-native/bright-wing-rim.png) | 4050,1810 | A broad pale curved edge separates textured body from a dark cavity. Many bright cyan/white glints sit in pale material. The curved edge is soft with a colored fringe. This is a halo/edge guard, but the visible rim could include real structure or illumination. |
| [thorax-texture](baseline-native/thorax-texture.png) | 4520,2560 | Small rounded cyan/green marks are separated by dark gaps; some merge into larger bright clusters. Tiny white/blue highlights are much harder than most marks. Countable marks and gap topology matter more than increased gradient energy. |
| [upper-leg-hairs](baseline-native/upper-leg-hairs.png) | 1820,640 | Multiple thin curved hairs protrude above and below a horizontal appendage. Several have blue/orange edge separation or a soft dark/colored surround. They are the strongest fine-structure guard: making them vanish, break or multiply is a regression even if the body looks cleaner. |
| [blue-joint](baseline-native/blue-joint.png) | 2680,850 | Saturated blue textured material lies above a greener reflective surface, separated by a dark curved band. Fine dark marks and pale strands remain visible in the blue. Preserve local blue-to-cyan/green relationships and small marks; desaturation can hide chromatic defects. |
| [upper-occlusion](baseline-native/upper-occlusion.png) | 3850,1300 | Blue raised material meets a dark recessed region and a lower textured surface. The lower contour has a soft pale cyan fringe and small intense green glints. No definitive doubled contour is established here. Do not remove the real contour or adjoining texture to suppress the fringe. |
| [eye-and-antenna](baseline-native/eye-and-antenna.png) | 5350,2920 | The native view shows a dark elongated gap between bright textured surfaces and fine strands near its upper-right edge; it does not establish an eye. Small colored specks remain in the gap. Use it for cross-depth surface/strand continuity and dark-gap contamination, not an eye-facet claim. |

The names `elytron-seam` and `eye-and-antenna` are retained so the frozen manifest
is immutable. Their anatomical interpretations above correct the original
overview-based role descriptions. No coordinates were moved after inspection.

## Acceptance for a later candidate

**ARGUED — prospective photographic criteria, not a measured score.**

1. Deliver and inspect the complete 299-frame candidate and the complete previous
   output. Use the same placement, crop/gauge and fixed display transform.
   Independent automatic tone fitting is a confound. Supply full-resolution
   masters and expose other-depth structures, not just the favored patch.
2. Inspect all ten unchanged witness rectangles with the same RGB16-to-PNG
   conversion and ICC. A visible gain should improve separability/continuity of
   actual small features while preserving hairs, weak dark structure and color.
3. Reject loss of the fine hairs, erased faint marks, larger merged scale blobs,
   changed gap topology, new duplicated edges, false colored texture, broadened
   highlight clipping or a changed background. Brightening/sharpening or a rise
   in gradient energy does not satisfy these criteria.
4. For a purported recovered or removed structure, confirm source support in
   a suitably focused source and check alignment locally. No source evidence is
   provided by this baseline-only inspection. A localized win with an unresolved
   whole-output regression is not a photographic improvement.
5. A weevil win alone does not address marigold ghosting/occlusion halos, mineral
   glare or flat-diagnostic artifacts. Those remain separate full-stack checks.
   This review contains no leading-stacker comparison and supports no competitive
   claim; comparable complete workflows remain required.

The first same-color direct-CFA candidate has no full photograph in this review.
Its rejection on neutral fine-detail controls must not be presented as a
photographic comparison or as proof that all RAW-domain alternatives fail.

## Executed review commands

Working directory: `C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl`.

```powershell
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/export-baseline.py
python -X faulthandler experiments/raw-quality-2026-10-26/photo-review/verify-baseline.py
```

The exporter exited 0 after verifying exact TIFF/PNG pixel and ICC round trips.
The independent readback command writes [inspection-receipt.json](inspection-receipt.json)
with source/crop hashes, dimensions, software versions and a deliberate pixel
mutation that the exact-equality check must reject. The visual calls were
`view_image(path=<full JPEG>, detail="original")`, followed by commissioning and
each of the ten PNG paths with the same option. A truncated multi-image tool
response was not credited; every crop was subsequently viewed separately.

No artifact observation above is a demonstrated fix. Softness and colored edge
appearance remain unresolved, and their division between optics, source focus,
alignment, merging and development is not established by this review.
