# Complete independent-view bundle review

MEASURED / VERIFIED: the full b16 underside and b18 top captures produce useful, separately inspectable photographs and focus evidence in their own coordinates. This realizes the bounded external-view export use: the underside exposes joints, ridges and recesses; the top exposes green scales, dorsal grooves and a compound eye. It does not estimate relative pose, intrinsics, metric depth or a3-D mesh. The engine producer was authored by the root agent; this complete photographic review is independent of that producer. I authored the UI importer/export workflow, so its checks below are author product verification.

## Command and retained output

The exact invocation is in outputs/multi-stack/completion/independent-views-run-14/receipt.json and [the frozen run plan](independent-views-full-run-plan.md). Frozen product14 CLI SHA2564906ad042a946c9d451d63b5f9512d899bff9124240004bc50ce2b4b2e2b797d processed all598 originals at8 workers and16GiB. Exit0; elapsed2337.179s; sampled peak private12,015,661,056bytes. Root jobs ran concurrently, so these are run observations, not isolated performance measurements. Each child has299 original acquisitions, its own alignment, native master, photograph and focus artifacts. Original corpora were read-only.

| View | Native photograph | Sensor origin | Focus cells / sensor origin | Direct fits / cycles | Reference |
| --- | --- | --- | --- | --- | --- |
| Underside | 6480×4320 | (276,184) | 3240×2160 / (276.5,184.5) | 1651 /1353 | local149 |
| Top green | 6536×4356 | (248,166) | 3268×2178 / (248.5,166.5) | 1730 /1432 | local149 |

Both are full3516×2344 quad gauges before their own crop. There is no parent alignment. Each view's original membership, ordinal mapping,49 bound artifacts, native/focus dimensions and parent/child hashes passed independent readback. All master values are finite; full TIFF decoding is bit-identical to mapped storage. Zero RGB counts287,719/466,416 are retained, not mislabeled invalid pixels or missing alpha. Reported invalid output pixels are0. Those numerical checks establish artifact integrity, not optical truth.

## Frozen display and witnesses

The first-view metadata alone set the display transform before either view was visually inspected. The independent display reproduced every first-view16-bit photograph channel exactly. Both complete PNGs and all crops use that fixed transform; each native384 origin was rounded/clamped from the predeclared own-view UV centers. No image fitting, resampling of crops, pixelwise cross-view comparison or candidate-driven recropping occurred. The whole6480×4320 and6536×4356 images were opened; the viewer displayed them at1920×1280 for orientation. All twelve384 crops were then opened at native size. The commissioned alternating-pixel384 witness remains visible and intact.

Evidence lives in outputs/multi-stack/completion/independent-views-review-14, including before-pixel-inspection.json, roi-frozen.json, fixed-transform.json, complete images, crop readbacks and artifact-audit.json. Commands and source hashes are retained in independent-views-review-freeze-14 and independent-views-review-readback-14. Readback used no RAW decoding and peaked at473,534,464private bytes.

| View / witness | Native origin | Observation |
| --- | --- | --- |
| Underside leg joint | (1234,2184) | Distinct ribbed/scaled surfaces; small bright colored points and softness remain. |
| Underside long ridge | (2530,2962) | Narrow ridge, crossing hairs and dark recesses remain separate. |
| Underside middle joint | (2983,1882) | Curved joint boundaries and transverse hairs visible; bright cyan/green fringe persists. |
| Underside head edge | (4409,1147) | Brown surface and dark cavity visible; some local blur. |
| Underside side scales | (4214,2789) | Ridges and fine hairs visible; lower-detail/soft patches remain. |
| Underside empty background | (5446,499) | Faint colored speckles in black field; not a temporal-noise measurement. |
| Top green left | (1115,1463) | Localized green reflections and dark scale boundaries. |
| Top green center | (2684,1420) | Bright pale/green feature with surrounding granular texture; some bloom. |
| Top neutral ridge | (3664,897) | Broad ridge and adjacent structures remain coherent, with local softness. |
| Top brown eye | (5102,1855) | Repeated facet pattern and eye rim remain visible; purple reflection retained. |
| Top eye lower rim | (5364,2639) | Rounded structures and dark gaps, plus bright colored highlights. |
| Top background | (3730,3641) | Frozen center lands on lower body, not empty background; retained without reselection. |

The complete views contain scattered colored speckles and some soft/colored halos. This capability does not cure those defects. There is no matched mainline baseline for these two newly processed views, so this review does not claim ordinary numerical/photographic nonregression, better resolution or noise reduction. The benefit is the complementary visible content and its usable bound export. Forcing these views into a single2-D warp would discard that intended distinction; no fabricated join is used as a reference.

## Product workflow

Product15 actual GPU controls imported this result, selected both views, saved the chosen output, reopened each in a separate process and exported both native-size PNG photographs. Focus overlays use their own3240×2160 and3268×2178 lattices; no primary selector or joint-alignment claim is shown. The complete103-file2,997,355,305byte bundle was exported through the product action, an existing destination refused, and the relocated bundle was strictly reimported with no original captures loaded. Parent receipts are byte-identical, original paths remain provenance, and no RAWs or unbound PNG edits were copied. [Desktop evidence](ui15-diversity-workflow-review.md) records commands and screenshots.

One actual-GPU defect was found: initial IndependentViews zoom8 was reset to1 during asynchronous reopen. The narrow fix and actual command-handler controls are frozen for product16; its GPU recheck remains due. That defect does not invalidate the full-image/native384 review, export bindings or completed relocation. Do not mark the zoom behavior verified until product16 images are inspected.
