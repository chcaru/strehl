# Bug2 complete-stack transfer: blanket CA-off fails

**VERIFIED — adverse photographic transfer.** Disabling the fixed optical
profile visibly increases red/cyan separation on pale fibres and flecks on this
second beetle. The effect appears on opposite sides of the field, not only one
favored patch. The complete image retains similar broad appearance, while its
orange texture remains soft/hazy. There is no convincing texture recovery to
offset the color-edge regression. Do not globally disable the profile on the
basis of the weevil hair improvement.

Both complete outputs and all ten native384 witnesses were inspected under one
display chosen from the baseline before candidate inspection. No original RAW
was read and no further source capture is needed for this bounded rejection.
Absolute color calibration and the physical reason for different behavior across
these two captures remain unestablished.

## Complete matched-display photographs

Baseline, optical-profile correction enabled:

![Complete bug2 baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/baseline/complete-stack.jpg)

[Full-resolution baseline RGB16 master](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/baseline/common-display-master.tiff)

Same complete 299-frame stack with profile correction disabled:

![Complete bug2 CA-off stack](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/ca-off/complete-stack.jpg)

[Full-resolution CA-off RGB16 master](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/ca-off/common-display-master.tiff)

Each master is 6566 × 4376. Complete JPEGs were displayed by the tool at
1920 × 1280 for orientation; native conclusions below use exact384 crops.
The original product masters remain at
[baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/bug2-100-baseline/stack-master.tiff)
and [CA-off](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/bug2-100-ca-off/stack-master.tiff).

## Frozen conditions

Input is all299 originals in `D:/personal/macro/insects/bug-2/100MSDCF`. Both arms
have the same source order, executable SHA256
`89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388`, and runtime map
SHA256 `5bbb0abcaeff627b25d7e4f94433ec9a5d010bce2f334f43a2a1601c1d17d459`.
The delivered-native gauge and dimensions match; the reference-native crop
offset is `(234,156)`. Original product master hashes are baseline
`42269774c8051a5c537c049d943e87f5aa35eb91f4b697cd786ecfc368e217f5` and CA-off
`f2d126de2fa839585d45626ed05a465f28ddecfa901b86b93c4c181c974c318a`.

`frozen-witnesses.json` and `baseline-inspection.json` record the sites and
baseline-only inspection before the candidate was seen. Gain4.993 came from the
baseline render log. Both retained pre-tone linear masters use that exact same
gain, clamp0..1, standard sRGB transfer and RGB16 rounding. PNG/JPEG conversion is
`(RGB16+128)//257`; original ICC is retained. No sharpening, local tone fitting,
denoising, new alignment or native-crop resampling was used.

The original automatic tone whites differ, `0.19560` versus `0.19584`; their
difference is excluded by the common display. Each arm's `receipt.json` binds
the source linear master, complete common master, full JPEG, ten TIFF/PNG crops,
display and executed producer. The renderer's commands/defaults/environment and
worker count remain in its own invocation and process receipts.

## All ten frozen witnesses

| Native site and origin | CA-off relative to baseline |
| --- | --- |
| dark-background `(6180,40)` | Fine colored grain and faint diagonal streaks persist. No noise improvement is established; this is not a calibrated flat. |
| green-fine-texture `(380,720)` | Pale flecks acquire more obvious red/cyan split edges. Fine green surface marks remain; increased chromatic contrast is not detail recovery. |
| left-green-rim `(100,2970)` | White fibres/glints near the far-left rim show stronger red/cyan separation. Broad dark rim and soft edge structure remain. |
| junction-white-strands `(990,2040)` | The curled pale strand and nearby flecks have stronger split coloring. Their continuity remains, but their appearance is worse. |
| orange-network-upper `(2820,430)` | Branches and nodes remain similarly diffuse with faint grain. No meaningful texture gain is established. |
| orange-network-lower `(1530,3460)` | Network continuity remains; isolated pale glints show stronger colored separation. Softness remains. |
| central-green-orange-rim `(2790,2160)` | Bright diagonal edge and broad cyan/dark surround remain. Changes are small; no coarse occlusion-contour fix. |
| central-seam `(4250,2970)` | Dark seam and blue/purple lower contour remain. Scattered flecks show altered/more split color; no clear detail gain. |
| right-reflective-orange `(5560,2560)` | Broad reflective haze and soft network persist. Fine color variations change, but there is no established structure recovery. |
| right-outer-fibres `(5960,900)` | Strongest opposite-field regression: pale web-like fibres acquire obvious red/cyan edge pairs, including bright upper and central strands. The fibres remain present; the extra color separation is not useful sharpness. |

The two-field regression is enough to reject blanket CA-off as a transferable
quality improvement. This review does not claim that the baseline's color is
perfect, that all its contours are physical, or that a single fixed profile is
optimal for every capture. It establishes that the weevil result cannot be
generalized by turning the current correction off everywhere.

**ARGUED next direction:** any capture-dependent CA measurement or applicability
rule should preserve the weevil's source-supported hair guard while also passing
these opposite-field fibre/fleck guards. Continue addressing the larger defects;
this ablation neither fixes the reflective haze nor restores fine orange texture.
No additional dataset expansion was performed for this review.

Commands executed, each exit0:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/prepare-display.py baseline
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/prepare-display.py ca-off
```

The observed renderer totals were 222.7s baseline and223.0s CA-off, but this review
makes no speed claim: these were root-scheduled operational runs, not an isolated
timing comparison. No Cargo build or reconstruction run was performed by this
review lane.
