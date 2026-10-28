# First complete repeat photograph review and frozen ROI mapping

Independent reviewer: root/independent_review, 2026-10-28. This is an interim observation record. Root released the completed insect-repeat-4 output after the geometry-only mapping was frozen. Pooled and only-pass controls on the same 598-frame map/domain are still required before attributing changes to repeat averaging. This reviewer ran no RAW decode, engine render or Cargo job.

## Exact geometry-only witness mapping

MEASURED command, run in the isolated worktree with Python 3.12.10, exit 0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/map-frozen-rois.py

The helper reads only saved JSON/text/source metadata. It never opens images. It parses f64 warp coefficients from their exact stored bit patterns, reproduces owned cover_scale with 60 bisection iterations and COVER_MARGIN_PX=3, and checks the cover_scale/cover_rect implementations against baseline commit c149e52834fc1c86c2af0fe022713c39fa25f33c. The reproduced legacy106 scale is 0.9824474577918777, bit-identical to the full-precision Scaled(...) record in sensor.tiff.json. The runtime baseline receipt confirms ordinary pyramid/default Scale, full-resolution gather and the matching optical profile.

Both maps use index149, the same original DSC00150.ARW with SHA256 e3d2046d5e718df10cb80c7108d9644adaa61189d992ea5b64b1ff8ffda25a06. An initial exact-identity guard correctly rejected the anchor coefficients: each differs from identity at approximately machine epsilon. The final helper retains both exact coefficient sets and transports through legacy anchor then inverse candidate anchor. Their effect is below 1e-10 output pixel and does not change any rounded origin. No image fitting was used.

Independently rebuilding native first-pass coverage, including the applied optical profile and CFA site offsets, gives scale 0.9785878769497705 and canvas [38,26,3440,2292] in plane pixels. This exactly matches the completed render receipt: 6880x4584 native output pixels, with full geometry 3516x2344 plane pixels.

The nominal mapping is u_candidate=C+k_legacy*(u_legacy-C)-2*crop_origin, with C=(3516,2344) in native output coordinates. The exact helper also preserves the legacy u/2 versus native (u-0.5)/2 guide conventions. A384-square witness center is the mean of its integer pixel-center coordinates, origin+191.5. The mapped continuous origin is rounded to nearest using floor(x+0.5); maximum absolute rounding error is0.499521710064073pixel. Identity, pure crop-shift and wrong-margin controls passed. No resampling is performed.

Frozen receipt: roi-mapped-frozen.json, SHA256 074084cce8d8d0788c3827f3872229593992c339a9eed33e3151af3ec2cd00a4. This was written before any candidate photographic content was viewed. The original nine baseline-selected witnesses and sizes were not changed.

| Witness | Candidate384 origin x,y |
| --- | --- |
| Dark background | 5631,575 |
| Cyan wing scales | 3028,2000 |
| Dark wing band | 2664,2098 |
| Upper leg hairs | 1525,664 |
| Wing-leg occlusion | 2438,2737 |
| Bright wing glint | 3323,1420 |
| Blue/cyan chroma | 2419,782 |
| Face edge | 4993,2923 |
| Antenna hairs | 5180,2412 |

The same physical anchor fixes a coordinate gauge, not placement truth. The legacy384-square covers384*k of the reference scene while the candidate384-square covers384. Legacy full-resolution demosaic gathering and native same-color CFA gathering differ; optical/channel and sample-phase behavior also differs. No cross-path pixelwise difference or noise subtraction is justified. Legacy107 has another physical reference, so its frozen origins supply broad landmark context only. Each forthcoming candidate arm must verify the identical saved598 warpmap and canvas before these origins are reused.

## Display and exact native crop commission

The released complete display uses only baseline106's frozen transform: black=-0.0002594062, white=0.20555225, contrast=0.55, exposure_gain=1. No candidate auto-tone or image-derived adjustment was used. Transform file SHA256 c6adc8f592bb83a49df8909b3475ad3a933e431260913f632efae0f42e7dcc3a. The candidate master is complete4584x6880 RGB32F, file SHA256 52894b57e3a4cd38dcab93302ff3a38e62c4d4b462cea937f562a9569d27a546. Complete fixed-display PNG SHA256 2bb59e45aa4ccbe6b45cab4af8dcd14ebb177edcea9866d92f01170f408d999c.

MEASURED command, exit0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/copy-frozen-native-crops.py insect-repeat-4

This checks complete-PNG/transform hashes, expected canvas, identical warpmap,6880x4584RGB shape and frozen ICC. It takes nine integer384x384 PNG slices without resizing or tone changes and verifies every output pixel after reopening. Receipt: native-crops/insect-repeat-4/receipt.json, SHA256 fc6e04f62e662072016f7ef2d24d960dabc431f281972deb228597c91885e5db. Crops were inspected with view_image detail=original.

## Observations; causal attribution pending

Complete fixed-display overviews of legacy106, legacy107 and repeat4 were inspected. Repeat4 has plausible complete framing and focus coverage, with no obvious missing anatomy, tiled seam or gross color discontinuity. Resized overview sharpness is not evidence. All nine repeat4 crops and all nine corresponding legacy106 crops were inspected at native384. Legacy107's occlusion, hairs, glint and chroma crops were also checked to resolve pass-dependent appearance.

| Witness | Observation under the common frozen display |
| --- | --- |
| Dark background | Faint diagonal colored tracks visible in legacy106 are less conspicuous in repeat4. Some sparse colored specks remain. This is not a temporal-noise or sqrt(K) measurement. |
| Cyan wing scales | Glint dots and their bright boundaries change size/shape; cyan cluster texture remains soft and granular. No resolved-detail gain is established by apparent brightness. |
| Dark wing band | Fine granular structure remains, with changed local brightness and dark contour placement. No broad erased band is obvious, but neither improvement nor loss is isolated from sampling/geometry. |
| Upper leg hairs | Fine hair tips remain; double/colored fringes are still visible and several lower contours look stronger in repeat4. Similar contours occur in legacy107. No clean deghosting claim. |
| Wing-leg occlusion | A much brighter green/blue underlying-leg region and textured lobe appear relative to legacy106. They also appear in legacy107, so this is a material pass-dependent appearance difference, not evidence of newly invented anatomy. The common-map controls must determine how it enters repeat4. |
| Bright wing glint | Bright islands change shape and intensity; fine repeated color texture remains. Display white cannot identify original photosite saturation or certify highlight recovery. |
| Blue/cyan chroma | Saturated blue textured surface and cyan transition remain; edge/ridge shapes differ subtly. No broad hue discontinuity is obvious. |
| Face edge | Curved dark eye boundary remains continuous. Surrounding bright texture changes; no new large seam is apparent. |
| Antenna hairs | Isolated filaments remain, with fine double/colored fringes retained. No clearly demonstrated resolved-tip gain from this cross-path comparison. |

ARGUED: these observations do not yet establish a net quality improvement or justify averaging claims. Joint geometry, original-CFA sampling, exposure/reflectance differences and repeat grouping are confounded against ordinary legacy outputs. The pending native pooled and only-pass0/1 arms on identical geometry/domain will separate those factors more directly. An explicit-primary versus no-primary control additionally changes disagreement fallback, so a no-repeat-grouping arm is a null for the whole grouping/fallback policy, not averaging alone.

## Released pooled598 control

The complete insect-pooled-4 overview and all nine frozen native384witnesses were independently inspected against repeat4 under the same display. copy-frozen-native-crops.py insect-pooled-4 exited0, verifying exact598warpmap, canvas, transform, ICC and pixel readback. Receipt SHA256 c6d050bdd5dea6f2e5dbbcd4839855f8b19906457e390791338ff7869a82f7e3.

No clear visible fine-detail, hair-separation or deghosting advantage from grouping was established in these witnesses. The conspicuous pass107-like occlusion content, hair fringes and altered glints relative to legacy106 are present in pooled as well. The complete overviews have no obvious relative framing or broad color difference. This is a limited inspected-witness judgment, not proof of equality or absence of a useful effect elsewhere.

MEASURED command compare-repeat-pooled-crops.py exited0. All nine RGB8native crops differ; mean absolute display-code deltas range0.0214-0.3883, with isolated maxima16-26. The greatest mean is the dark background, then blue/cyan chroma. Exact per-witness counts are in repeat-versus-pooled-crop-differences.json. These are display-code change magnitudes, not perceptual-quality or temporal-noise metrics; no cross-gauge pixel comparison was performed.

The producing path is active: repeat4 reports480groups and889,604,344averaged finest-level group coefficients, while pooled reports598singleton groups and0averaged coefficients. These are accumulated per-group/band mechanics, not output pixel counts or a quality score. Thus visual similarity is not a no-op finding. Only-pass controls remain needed to separate native sampling/joint-geometry changes from including another acquisition pass.
